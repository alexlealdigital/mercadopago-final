from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import os

# --- Configuração do Flask e SQLAlchemy ---
app = Flask(__name__)

# Configuração do Banco de Dados - ESSA PARTE É CRUCIAL
# A Vercel não tem um banco de dados por padrão. Você precisa usar um serviço externo
# como Neon, Supabase, ou ElephantSQL (PostgreSQL) e colocar a URL de conexão
# em uma variável de ambiente chamada DATABASE_URL.
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    # Se a variável não estiver definida, a API vai quebrar, mas com uma mensagem clara.
    raise RuntimeError("DATABASE_URL não está configurada.")

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa o db com a aplicação Flask
# Importamos o modelo DEPOIS de configurar o app
from cobrancas_model import db, Cobranca
db.init_app(app)


# --- Rota da API ---
@app.route('/api/cobrancas', methods=['GET'])
def get_cobrancas():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    try:
        with app.app_context():
            # Exemplo de como buscar os dados no banco
            # paginacao = Cobranca.query.paginate(page=page, per_page=per_page, error_out=False)
            # cobrancas_list = [c.to_dict() for c in paginacao.items]
            
            # Por enquanto, vamos retornar sucesso sem tocar no banco
            cobrancas_list = []

        return jsonify({
            'message': 'API de Cobranças funcionando!',
            'data': cobrancas_list,
            # 'total': paginacao.total,
            # 'pages': paginacao.pages,
            # 'current_page': page
        })

    except Exception as e:
        # Retorna um erro claro se algo der errado
        return jsonify({'error': str(e)}), 500

