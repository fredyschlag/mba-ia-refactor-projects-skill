const logger = require('../utils/logger');

function errorHandler(err, req, res, next) {
    logger.error(err.stack || err.message);
    res.status(500).json({ erro: 'Erro interno' });
}

module.exports = errorHandler;
