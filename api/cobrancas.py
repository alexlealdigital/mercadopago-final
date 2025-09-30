from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
import os

# Inicializa o Flask
app = Flask(__name__)

# Configuração do Banco de Dados
# A Vercel vai preencher esta variável de ambiente
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    # Este erro aparecerá nos logs se a variável não estiver configurada
    raise RuntimeError("DATABASE_URL não está configurada.")

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
# ... logo após db = SQLAlchemy(app)

# Importe o modelo de dados
from .cobrancas_model import Cobranca

# Bloco para criar a tabela antes da primeira requisição
with app.app_context():
    db.create_all()

# ... o resto do seu código da API continua aqui


# A rota da API
@app.route('/api/cobrancas', methods=['GET'])
def get_cobrancas():
    # Lógica para buscar cobranças do banco de dados virá aqui
    # Por enquanto, apenas retornamos uma mensagem de sucesso
    return jsonify({
        "status": "success",
        "message": "API de cobranças está funcionando!",
        "data": [] 
    }), 200

# Esta rota é opcional, mas boa para testar a raiz
@app.route('/', methods=['GET'])
def index():
    return "Servidor Flask está no ar!"

