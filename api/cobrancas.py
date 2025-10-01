from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import os

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

# 7. Definição da Rota POST para CRIAR cobranças
@app.route('/api/cobrancas', methods=['POST'])
def create_cobranca():
    try:
        # Pega os dados enviados pelo frontend
        dados = request.get_json()

        # Validação simples (pode ser melhorada depois)
        if not dados or not dados.get('external_reference') or not dados.get('cliente_nome'):
            return jsonify({"status": "error", "message": "Dados incompletos."}), 400

        # Cria um novo objeto Cobranca
        nova_cobranca = Cobranca(
            external_reference=dados['external_reference'],
            cliente_nome=dados['cliente_nome'],
            cliente_email=dados.get('cliente_email'),
            valor=dados.get('valor'),
            status=dados.get('status', 'pending')
        )

        # Adiciona ao banco de dados
        db.session.add(nova_cobranca)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Cobrança criada com sucesso!",
            "data": nova_cobranca.to_dict()
        }), 201 # 201 significa "Created"
    
    except Exception as e:
        db.session.rollback() # Desfaz a transação em caso de erro
        return jsonify({"status": "error", "message": f"Erro ao criar cobrança: {str(e)}"}), 500




