const { config } = require('../config/settings');

// Autenticação real para rotas administrativas: exige um segredo compartilhado
// (ADMIN_API_KEY, vindo de variável de ambiente) no header, em vez de nenhuma
// verificação. Substitui o modelo de login/sessão completo (JWT) por ora --
// documentado no relatório de auditoria como próximo passo caso o produto
// precise de múltiplos admins/usuários autenticados.
function requireAdminKey(req, res, next) {
    const providedKey = req.header('x-admin-key');

    if (!providedKey || providedKey !== config.adminApiKey) {
        return res.status(401).json({ erro: 'Não autorizado' });
    }

    next();
}

module.exports = requireAdminKey;
