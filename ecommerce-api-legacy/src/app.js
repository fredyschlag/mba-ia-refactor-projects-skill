const express = require('express');
const { config } = require('./config/settings');
const { initDb } = require('./database/connection');
const errorHandler = require('./middlewares/errorHandler');
const checkoutRoutes = require('./routes/checkoutRoutes');
const adminRoutes = require('./routes/adminRoutes');
const userRoutes = require('./routes/userRoutes');
const logger = require('./utils/logger');

const app = express();
app.use(express.json());

initDb();

app.use('/api', checkoutRoutes);
app.use('/api', adminRoutes);
app.use('/api', userRoutes);

app.use(errorHandler);

app.listen(config.port, () => {
    logger.info(`Frankenstein LMS rodando na porta ${config.port}...`);
});

module.exports = app;
