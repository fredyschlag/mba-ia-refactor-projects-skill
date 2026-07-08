const User = require('../models/User');
const Enrollment = require('../models/Enrollment');
const Payment = require('../models/Payment');

async function deleteUser(req, res, next) {
    try {
        const { id } = req.params;

        const enrollments = await Enrollment.findByUserId(id);
        const enrollmentIds = enrollments.map((enrollment) => enrollment.id);

        await Payment.deleteByEnrollmentIds(enrollmentIds);
        await Enrollment.deleteByUserId(id);
        const deletedCount = await User.delete(id);

        if (deletedCount === 0) {
            return res.status(404).json({ erro: 'Usuário não encontrado' });
        }

        res.status(200).json({ msg: 'Usuário e registros relacionados removidos com sucesso' });
    } catch (err) {
        next(err);
    }
}

module.exports = { deleteUser };
