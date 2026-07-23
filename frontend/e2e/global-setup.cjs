const fs = require('fs');
const path = require('path');

async function globalSetup() {
  try {
    const configPath = path.resolve(__dirname, '../../../../config/servers.json');
    if (fs.existsSync(configPath)) {
      const configFile = fs.readFileSync(configPath, 'utf8');
      const config = JSON.parse(configFile);
      if (config?.servers?.dev) {
        process.env.INVENTREE_USERNAME = config.servers.dev.username || 'admin';
        process.env.INVENTREE_PASSWORD = config.servers.dev.password || 'admin';
        process.env.INVENTREE_BASE_URL = config.servers.dev.url || 'http://localhost:8001';
        console.log('Loaded dev server config from config/servers.json');
      }
    } else {
      console.log('config/servers.json not found, using default credentials');
    }
  } catch (error) {
    console.log('Error loading config/servers.json, using default credentials');
  }
}

module.exports = globalSetup;
