const { db } = require('../database/connection');
const { PAYMENT_STATUS } = require('../utils/constants');

class Course {
    static findActiveById(id) {
        return new Promise((resolve, reject) => {
            db.get('SELECT * FROM courses WHERE id = ? AND active = 1', [id], (err, row) => {
                if (err) return reject(err);
                resolve(row);
            });
        });
    }

    // Substitui o antigo loop N+1 (1 query de cursos + 1 por matrícula + 2 por aluno)
    // por um único JOIN, agregado em memória.
    static findFinancialReport() {
        const sql = `
            SELECT
                c.id AS course_id,
                c.title AS course_title,
                e.id AS enrollment_id,
                u.name AS student_name,
                p.amount AS paid_amount,
                p.status AS payment_status
            FROM courses c
            LEFT JOIN enrollments e ON e.course_id = c.id
            LEFT JOIN users u ON u.id = e.user_id
            LEFT JOIN payments p ON p.enrollment_id = e.id
            ORDER BY c.id
        `;

        return new Promise((resolve, reject) => {
            db.all(sql, [], (err, rows) => {
                if (err) return reject(err);

                const reportByCourseId = new Map();

                rows.forEach((row) => {
                    if (!reportByCourseId.has(row.course_id)) {
                        reportByCourseId.set(row.course_id, {
                            course: row.course_title,
                            revenue: 0,
                            students: [],
                        });
                    }

                    if (row.enrollment_id === null) return;

                    const courseData = reportByCourseId.get(row.course_id);

                    if (row.payment_status === PAYMENT_STATUS.PAID) {
                        courseData.revenue += row.paid_amount;
                    }

                    courseData.students.push({
                        student: row.student_name || 'Unknown',
                        paid: row.paid_amount || 0,
                    });
                });

                resolve(Array.from(reportByCourseId.values()));
            });
        });
    }
}

module.exports = Course;
