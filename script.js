document.addEventListener('DOMContentLoaded', () => {
    // Seleciona o formulário de criação de cobrança
    const formCobranca = document.getElementById('form-cobranca');

    // Seleciona a área para mostrar o resultado (modal)
    const modal = document.getElementById('modal-detalhes');
    const modalBody = document.getElementById('modal-body');
    const modalClose = document.querySelector('.modal-close');

    // Adiciona um "ouvinte" para o ENVIO do formulário
    formCobranca.addEventListener('submit', async (event) => {
        // Previne o comportamento padrão do formulário (que é recarregar a página)
        event.preventDefault();

        // Pega os dados do formulário
        const formData = new FormData(formCobranca);
        const dadosCobranca = Object.fromEntries(formData.entries());

        // Mostra uma mensagem de "carregando"
        showLoadingInModal();

        try {
            // CHAMA A NOSSA API (MÉTODO POST)
            const response = await fetch('/api/cobrancas', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                // Envia todos os dados do formulário para o backend
                body: JSON.stringify(dadosCobranca),
            });

            const result = await response.json();

            if (response.ok) {
                // SUCESSO! Mostra o QR Code no Modal
                showQrCodeInModal(result);
            } else {
                // Se a API retornar um erro
                throw new Error(result.message || 'Ocorreu um erro ao gerar a cobrança.');
            }

        } catch (error) {
            // Se houver um erro de rede ou na API
            showErrorInModal(error.message);
        }
    });

    // Funções auxiliares para controlar o Modal
    function showLoadingInModal() {
        modalBody.innerHTML = '<p>Gerando sua cobrança, aguarde...</p>';
        modal.style.display = 'block';
    }

    function showQrCodeInModal(data) {
        modalBody.innerHTML = `
            <h2>Pague com PIX para confirmar!</h2>
            <img src="data:image/jpeg;base64,${data.qr_code_base64}" alt="PIX QR Code" style="max-width: 100%;">
            <p>Ou copie e cole o código:</p>
            <textarea readonly style="width: 100%; min-height: 100px;">${data.qr_code_text}</textarea>
        `;
    }

    function showErrorInModal(message) {
        modalBody.innerHTML = `<p style="color: red;"><b>Erro:</b> ${message}</p>`;
        modal.style.display = 'block';
    }

    // Fecha o modal ao clicar no 'X'
    modalClose.addEventListener('click', () => {
        modal.style.display = 'none';
    });

    // Fecha o modal ao clicar fora dele
    window.addEventListener('click', (event) => {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    });

    // Lógica para trocar de abas (já que seu HTML tem isso)
    const navButtons = document.querySelectorAll('.nav-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    navButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove a classe 'active' de todos
            navButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(tab => tab.classList.remove('active'));

            // Adiciona 'active' ao botão e tab clicados
            button.classList.add('active');
            document.getElementById(`tab-${button.dataset.tab}`).classList.add('active');
        });
    });

    // A função para carregar a lista de cobranças pode ser adicionada aqui depois
    // Por enquanto, vamos focar em criar a cobrança.
});
