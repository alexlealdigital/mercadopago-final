document.addEventListener('DOMContentLoaded', () => {
    const buyButton = document.getElementById('buy-button');
    const emailInput = document.getElementById('customer-email');
    const paymentFeedback = document.getElementById('payment-feedback');

    // Adiciona um "ouvinte" para o clique no botão
    buyButton.addEventListener('click', async () => {
        const email = emailInput.value;

        // Validação simples do email
        if (!email || !email.includes('@')) {
            paymentFeedback.innerHTML = '<p style="color: red;">Por favor, insira um e-mail válido.</p>';
            return;
        }

        // Mostra uma mensagem de "carregando"
        paymentFeedback.innerHTML = '<p>Gerando seu QR Code, aguarde...</p>';
        buyButton.disabled = true; // Desabilita o botão para evitar cliques duplos

        try {
            // CHAMA A NOSSA API (MÉTODO POST)
            const response = await fetch('/api/cobrancas', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email: email }), // Envia o email para o backend
            });

            const result = await response.json();

            if (response.ok) {
                // SUCESSO! Mostra o QR Code
                paymentFeedback.innerHTML = `
                    <h2>Pague com PIX para receber seu e-book!</h2>
                    <img src="data:image/jpeg;base64,${result.qr_code_base64}" alt="PIX QR Code">
                    <p>Ou copie e cole o código:</p>
                    <textarea readonly>${result.qr_code_text}</textarea>
                `;
            } else {
                // Se a API retornar um erro
                throw new Error(result.message || 'Ocorreu um erro.');
            }

        } catch (error) {
            // Se houver um erro de rede ou na API
            paymentFeedback.innerHTML = `<p style="color: red;">Erro ao criar cobrança: ${error.message}</p>`;
            buyButton.disabled = false; // Habilita o botão novamente
        }
    });
});
