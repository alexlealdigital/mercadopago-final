from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import os
import mercadopago

# 1. Inicialização do Flask
app = Flask(__name__)

# 2. Configuração do Banco de Dados

db_url = "postgresql://postgres.fkxwoaixpxwyeqbmkisp:K9pWzL7jR2mXbV4qGfA3sE8h@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"


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
        # 1. Pega o email que o cliente digitou no site
        dados = request.get_json()
        email_cliente = dados.get('email')

        if not email_cliente:
            return jsonify({"status": "error", "message": "O email é obrigatório."}), 400

        # 2. Prepara para falar com o Mercado Pago
        sdk = mercadopago.SDK(os.environ.get('MERCADOPAGO_ACCESS_TOKEN'))

        # 3. Define os detalhes do produto (seu e-book)
        valor_ebook = 19.99  # Defina o preço aqui
        descricao_ebook = "Seu E-book Incrível" # Defina a descrição aqui

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
        payment = payment_response["response"]

        # 5. Pega o QR Code que o Mercado Pago retornou
        qr_code_base64 = payment['point_of_interaction']['transaction_data']['qr_code_base64']
        qr_code_text = payment['point_of_interaction']['transaction_data']['qr_code']

        # (Opcional, mas bom) Salva um registro no seu banco de dados
        nova_cobranca = Cobranca(
            external_reference=str(payment['id']),
            cliente_nome="Cliente do E-book",
            cliente_email=email_cliente,
            valor=valor_ebook,
            status=payment['status']
        )
        db.session.add(nova_cobranca)
        db.session.commit()

        # 6. ENVIA O QR CODE DE VOLTA PARA O SITE
        return jsonify({
            "status": "success",
            "message": "Cobrança PIX criada!",
            "qr_code_base64": qr_code_base64,
            "qr_code_text": qr_code_text
        }), 201

    except Exception as e:
        db.session.rollback()
        # Retorna uma mensagem de erro clara se algo falhar
        return jsonify({"status": "error", "message": f"Erro ao criar cobrança no Mercado Pago: {str(e)}"}), 500




