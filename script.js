from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import json
import os
import mercadopago

# 1. Inicialização do Flask
app = Flask(__name__)

# 2. Configuração de CORS para permitir requisições do frontend
CORS(app, origins="*")

# 3. Configuração do Banco de Dados
# Usa PostgreSQL em produção ou SQLite em desenvolvimento
db_url = os.environ.get('DATABASE_URL', 'sqlite:///cobrancas.db')

# Fix para Heroku PostgreSQL URL
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 3. Inicialização do SQLAlchemy
db = SQLAlchemy(app)

# 4. DEFINIÇÃO DO MODELO (Tudo em um só arquivo)
class Cobranca(db.Model):
    __tablename__ = 'cobrancas'
    id = db.Column(db.Integer, primary_key=True)
    external_reference = db.Column(db.String(100), unique=True, nullable=False)
    cliente_nome = db.Column(db.String(200), nullable=False)
    cliente_email = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='pending', nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'external_reference': self.external_reference,
            'cliente_nome': self.cliente_nome,
            'cliente_email': self.cliente_email,
            'valor': self.valor,
            'status': self.status,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None
        }

# 5. Criação da Tabela no Banco de Dados
with app.app_context():
    db.create_all()

# 6. Definição da Rota da API
@app.route('/api/cobrancas', methods=['GET'])
def get_cobrancas():
    try:
        cobrancas_db = Cobranca.query.order_by(Cobranca.data_criacao.desc()).all()
        cobrancas_list = [cobranca.to_dict() for cobranca in cobrancas_db]
        return jsonify({
            "status": "success",
            "message": "Cobranças recuperadas com sucesso!",
            "data": cobrancas_list
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro ao acessar o banco de dados: {str(e)}"}), 500

# ROTA PARA CRIAR UMA NOVA COBRANÇA (MÉTODO POST)
@app.route('/api/cobrancas', methods=['POST'])
def create_cobranca():
    try:
        # 1. Pega os dados enviados pelo frontend
        dados = request.get_json()
        
        # Debug: Log dos dados recebidos
        print(f"Dados recebidos: {dados}")
        
        # Validação melhorada dos campos obrigatórios
        if not dados:
            return jsonify({"status": "error", "message": "Nenhum dado foi enviado."}), 400
            
        email_cliente = dados.get('email')
        nome_cliente = dados.get('nome', 'Cliente do E-book')
        
        if not email_cliente:
            return jsonify({"status": "error", "message": "O email é obrigatório."}), 400

        # Validação básica de email
        if '@' not in email_cliente or '.' not in email_cliente:
            return jsonify({"status": "error", "message": "Por favor, insira um email válido."}), 400

        # 2. Prepara para falar com o Mercado Pago
        access_token = os.environ.get('MERCADOPAGO_ACCESS_TOKEN')
        if not access_token:
            return jsonify({"status": "error", "message": "Token do Mercado Pago não configurado."}), 500
            
        sdk = mercadopago.SDK(access_token)

        # 3. Define os detalhes do produto (seu e-book)
        valor_ebook = float(dados.get('valor', 19.99))  # Permite valor customizado ou usa padrão
        descricao_ebook = dados.get('titulo', "Seu E-book Incrível")  # Permite título customizado

        payment_data = {
            "transaction_amount": valor_ebook,
            "description": descricao_ebook,
            "payment_method_id": "pix",
            "payer": {
                "email": email_cliente
            }
        }

        # 4. ENVIA A ORDEM PARA O MERCADO PAGO
        payment_response = sdk.payment().create(payment_data)
        
        # Verifica se a resposta do Mercado Pago foi bem-sucedida
        if payment_response["status"] != 201:
            error_msg = payment_response.get("response", {}).get("message", "Erro desconhecido do Mercado Pago")
            return jsonify({"status": "error", "message": f"Erro do Mercado Pago: {error_msg}"}), 500
            
        payment = payment_response["response"]

        # 5. Pega o QR Code que o Mercado Pago retornou
        qr_code_base64 = payment['point_of_interaction']['transaction_data']['qr_code_base64']
        qr_code_text = payment['point_of_interaction']['transaction_data']['qr_code']

        # 6. Salva um registro no seu banco de dados
        nova_cobranca = Cobranca(
            external_reference=str(payment['id']),
            cliente_nome=nome_cliente,
            cliente_email=email_cliente,
            valor=valor_ebook,
            status=payment['status']
        )
        db.session.add(nova_cobranca)
        db.session.commit()

        # 7. ENVIA O QR CODE DE VOLTA PARA O SITE
        return jsonify({
            "status": "success",
            "message": "Cobrança PIX criada com sucesso!",
            "qr_code_base64": qr_code_base64,
            "qr_code_text": qr_code_text,
            "payment_id": payment['id'],
            "valor": valor_ebook
        }), 201

    except Exception as e:
        db.session.rollback()
        # Log do erro para debug
        print(f"Erro ao criar cobrança: {str(e)}")
        # Retorna uma mensagem de erro clara se algo falhar
        return jsonify({"status": "error", "message": f"Erro ao criar cobrança: {str(e)}"}), 500

# Rota para verificar se a API está funcionando
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "success", "message": "API funcionando corretamente!"}), 200

# Rota raiz para verificação
@app.route('/', methods=['GET'])
def root():
    return jsonify({
        "status": "success", 
        "message": "Sistema de Cobrança - API Backend",
        "version": "1.0.0",
        "endpoints": [
            "GET /api/health - Health check",
            "POST /api/cobrancas - Criar cobrança",
            "GET /api/cobrancas - Listar cobranças"
        ]
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
