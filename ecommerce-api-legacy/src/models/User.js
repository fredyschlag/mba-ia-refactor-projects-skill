const bcrypt = require('bcryptjs');
const { db } = require('../database/connection');

const SALT_ROUNDS = 10;

class User {
    static findByEmail(email) {
        return new Promise((resolve, reject) => {
            db.get('SELECT * FROM users WHERE email = ?', [email], (err, row) => {
                if (err) return reject(err);
                resolve(row);
            });
        });
    }

    static async create({ name, email, password }) {
        const passwordHash = await User.hashPassword(password);

        return new Promise((resolve, reject) => {
            db.run(
                'INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
                [name, email, passwordHash],
                function (err) {
                    if (err) return reject(err);
                    resolve({ id: this.lastID, name, email });
                }
            );
        });
    }

    static hashPassword(password) {
        return bcrypt.hash(password, SALT_ROUNDS);
    }

    static verifyPassword(user, password) {
        return bcrypt.compare(password, user.pass);
    }

    static delete(id) {
        return new Promise((resolve, reject) => {
            db.run('DELETE FROM users WHERE id = ?', [id], function (err) {
                if (err) return reject(err);
                resolve(this.changes);
            });
        });
    }
}

module.exports = User;
