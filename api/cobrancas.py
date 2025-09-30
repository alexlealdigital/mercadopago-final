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
    try:
        # Busca todas as cobranças no banco de dados
        cobrancas_db = Cobranca.query.order_by(Cobranca.data_criacao.desc()).all()
        
        # Converte os objetos de cobrança para dicionários
        cobrancas_list = [cobranca.to_dict() for cobranca in cobrancas_db]
        
        return jsonify({
            "status": "success",
            "message": "Cobranças recuperadas com sucesso!",
            "data": cobrancas_list
        }), 200
    except Exception as e:
        # Se algo der errado, retorna um erro 500 com a mensagem
        return jsonify({"status": "error", "message": str(e)}), 500



