from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import os

# 1. Inicialização do Flask
app = Flask(__name__)

# 2. Configuração do Banco de Dados
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    raise RuntimeError("A variável de ambiente DATABASE_URL não foi encontrada.")

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
