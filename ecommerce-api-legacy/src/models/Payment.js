const { db } = require('../database/connection');
const { PAYMENT_STATUS } = require('../utils/constants');

const APPROVED_CARD_PREFIX = '4';

class Payment {
    static approve(cardNumber) {
        return cardNumber.startsWith(APPROVED_CARD_PREFIX) ? PAYMENT_STATUS.PAID : PAYMENT_STATUS.DENIED;
    }

    static create(enrollmentId, amount, status) {
        return new Promise((resolve, reject) => {
            db.run(
                'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
                [enrollmentId, amount, status],
                function (err) {
                    if (err) return reject(err);
                    resolve(this.lastID);
                }
            );
        });
    }

    static deleteByEnrollmentIds(enrollmentIds) {
        if (enrollmentIds.length === 0) return Promise.resolve(0);

        const placeholders = enrollmentIds.map(() => '?').join(', ');

        return new Promise((resolve, reject) => {
            db.run(
                `DELETE FROM payments WHERE enrollment_id IN (${placeholders})`,
                enrollmentIds,
                function (err) {
                    if (err) return reject(err);
                    resolve(this.changes);
                }
            );
        });
    }
}

module.exports = Payment;
