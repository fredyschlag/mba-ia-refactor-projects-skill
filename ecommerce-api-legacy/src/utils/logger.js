function timestamp() {
    return new Date().toISOString();
}

const logger = {
    info: (message) => console.log(`[INFO] ${timestamp()} ${message}`),
    error: (message) => console.error(`[ERROR] ${timestamp()} ${message}`),
};

module.exports = logger;
