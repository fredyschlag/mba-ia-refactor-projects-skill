const express = require('express');
const userController = require('../controllers/userController');
const requireAdminKey = require('../middlewares/requireAdminKey');

const router = express.Router();

router.delete('/users/:id', requireAdminKey, userController.deleteUser);

module.exports = router;
