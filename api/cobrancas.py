from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
import os

# 1. Inicialização do Flask
app = Flask(__name__)

# 2. Configuração do Banco de Dados a partir das Variáveis de Ambiente
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    raise RuntimeError("A variável de ambiente DATABASE_URL não foi encontrada.")

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 3. Inicialização do SQLAlchemy
db = SQLAlchemy(app)

# 4. Importação do Modelo de Dados (CORREÇÃO APLICADA AQUI)
# Removemos o ponto antes de "cobrancas_model" para que a importação funcione na Vercel.
from cobrancas_model import Cobranca

# 5. Criação da Tabela no Banco de Dados
# Este bloco garante que a tabela 'cobrancas' seja criada se ainda não existir.
with app.app_context():
    db.create_all()

# 6. Definição da Rota da API
@app.route('/api/cobrancas', methods=['GET'])
def get_cobrancas():
    """
    Busca todas as cobranças no banco de dados e as retorna como JSON.
    """
    try:
        # Busca todas as cobranças, ordenando pelas mais recentes primeiro
        cobrancas_db = Cobranca.query.order_by(Cobranca.data_criacao.desc()).all()
        
        # Converte a lista de objetos SQLAlchemy para uma lista de dicionários
        cobrancas_list = [cobranca.to_dict() for cobranca in cobrancas_db]
        
        # Retorna a resposta de sucesso com os dados
        return jsonify({
            "status": "success",
            "message": "Cobranças recuperadas com sucesso!",
            "data": cobrancas_list
        }), 200
    except Exception as e:
        # Em caso de qualquer erro durante a busca, retorna uma mensagem de erro clara.
        # Isso é útil para depurar problemas de banco de dados no futuro.
        return jsonify({"status": "error", "message": f"Erro ao acessar o banco de dados: {str(e)}"}), 500

# Rota opcional para testar se o servidor está no ar
@app.route('/', methods=['GET'])
def index():
    return "Servidor Flask da API de Cobranças está no ar!"

