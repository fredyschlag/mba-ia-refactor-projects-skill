const User = require('../models/User');
const Course = require('../models/Course');
const Enrollment = require('../models/Enrollment');
const Payment = require('../models/Payment');
const AuditLog = require('../models/AuditLog');
const logger = require('../utils/logger');
const { PAYMENT_STATUS, DEFAULT_PASSWORD } = require('../utils/constants');

async function checkout(req, res, next) {
    try {
        const { usr: username, eml: email, pwd: password, c_id: courseId, card: cardNumber } = req.body;

        if (!username || !email || !courseId || !cardNumber) {
            return res.status(400).send('Bad Request');
        }

        const course = await Course.findActiveById(courseId);
        if (!course) return res.status(404).send('Curso não encontrado');

        let user = await User.findByEmail(email);

        if (!user) {
            user = await User.create({ name: username, email, password: password || DEFAULT_PASSWORD });
        } else {
            const passwordMatches = password && (await User.verifyPassword(user, password));
            if (!passwordMatches) return res.status(401).send('Credenciais inválidas');
        }

        const status = Payment.approve(cardNumber);
        logger.info(`Processando pagamento do curso ${courseId} para usuário ${user.id}`);

        if (status === PAYMENT_STATUS.DENIED) {
            return res.status(400).send('Pagamento recusado');
        }

        const enrollmentId = await Enrollment.create(user.id, courseId);
        await Payment.create(enrollmentId, course.price, status);
        await AuditLog.record(`Checkout curso ${courseId} por ${user.id}`);

        res.status(200).json({ msg: 'Sucesso', enrollment_id: enrollmentId });
    } catch (err) {
        next(err);
    }
}

module.exports = { checkout };
