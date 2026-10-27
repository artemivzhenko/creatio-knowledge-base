import { execSync } from 'child_process';
import { readFileSync } from 'fs';
import { dirname, resolve, join } from 'path';
import { fileURLToPath } from 'url';
import { updateExcludedModules } from './common.js';

const tempDeviceModulePath = '/sdcard/main.debug.js';
const tempDeviceExcludedModulesPath = '/sdcard/excluded-modules.json';
const finalDeviceModulePath = '/sdcard/Android/data/com.creatio.mobileapp/files/creatio/debugthis/main.debug.js';
const finalDeviceExcludedModulesPath = '/sdcard/Android/data/com.creatio.mobileapp/files/creatio/debugthis/excluded-modules.json';

const __dirname = dirname(fileURLToPath(import.meta.url));

const config = JSON.parse(readFileSync(resolve(__dirname, '../creatio-mobile-config.json'), 'utf8'));

const sourcePath = join(__dirname, '..', 'out', 'mobile', config['moduleName'], 'main.debug.js');

const excludedModulesPath = join(__dirname, '..', 'out', 'excluded-modules.json');

function executeCommand(command) {
    try {
        const output = execSync(command, { encoding: 'utf8' });
        console.log(output);
        return output;
    } catch (error) {
        console.error(`Error: ${error.message}`);
        throw error;
    }
}

function injectOnDevice() {
    try {
        updateExcludedModules(config['moduleName'], excludedModulesPath);
        executeCommand(`adb push "${sourcePath}" ${tempDeviceModulePath}`);
        executeCommand(`adb push "${excludedModulesPath}" ${tempDeviceExcludedModulesPath}`);
        console.log('File pushed to device');


		executeCommand(`adb shell "mkdir -p /sdcard/Android/data/com.creatio.mobileapp/files/creatio/debugthis/"`);
        executeCommand(`adb shell "mv ${tempDeviceModulePath} ${finalDeviceModulePath}"`);
        executeCommand(`adb shell "mv ${tempDeviceExcludedModulesPath} ${finalDeviceExcludedModulesPath}"`);
        console.log('File moved to final location');

        console.log('Injection completed successfully');
    } catch (error) {
        console.error('An error occurred during injection:', error);
    }
}

injectOnDevice();
