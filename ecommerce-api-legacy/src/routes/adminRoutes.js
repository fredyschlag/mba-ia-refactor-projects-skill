const express = require('express');
const adminController = require('../controllers/adminController');
const requireAdminKey = require('../middlewares/requireAdminKey');

const router = express.Router();

router.get('/admin/financial-report', requireAdminKey, adminController.getFinancialReport);

module.exports = router;
