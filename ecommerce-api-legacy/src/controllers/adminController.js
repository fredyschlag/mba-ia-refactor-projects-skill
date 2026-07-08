const Course = require('../models/Course');

async function getFinancialReport(req, res, next) {
    try {
        const report = await Course.findFinancialReport();
        res.json(report);
    } catch (err) {
        next(err);
    }
}

module.exports = { getFinancialReport };
