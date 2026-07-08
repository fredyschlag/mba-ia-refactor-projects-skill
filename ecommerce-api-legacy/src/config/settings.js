require('dotenv').config();

function required(name) {
    const value = process.env[name];
    if (!value) {
        throw new Error(`Variável de ambiente obrigatória ausente: ${name}`);
    }
    return value;
}

const config = {
    port: Number(process.env.PORT) || 3000,
    dbUser: required('DB_USER'),
    dbPass: required('DB_PASS'),
    paymentGatewayKey: required('PAYMENT_GATEWAY_KEY'),
    smtpUser: required('SMTP_USER'),
    adminApiKey: required('ADMIN_API_KEY'),
};

module.exports = { config };
