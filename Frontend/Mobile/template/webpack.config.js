import path from "path";
import { fileURLToPath } from 'url';
import { readFileSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const creatioMobileConfig = JSON.parse(
  readFileSync(path.resolve(__dirname, 'creatio-mobile-config.json'), 'utf8')
);

const baseConfig = {
    mode: 'development',
    entry: './src/index.ts',
    output: {
        path: path.resolve('out/mobile', creatioMobileConfig.moduleName),
        iife: true,
        globalObject: 'this'
    },
    externals: {
        "@creatio/mobile-common": "crtSdk",
    },
    resolve: {
        conditionNames: ['es2015'],
        extensions: [".ts", ".js"],
    },
    module: {
        rules: [
            {
                test: /\.ts$/,
                loader: "ts-loader",
                exclude: /node_modules/,
            }
        ]
    }
};

const inlineSourceMapConfig = {
    ...baseConfig,
    devtool: "inline-source-map",
    output: {
        ...baseConfig.output,
        filename: "main.debug.js",
    }
};

const separateSourceMapConfig = {
    ...baseConfig,
    devtool: "source-map",
    output: {
        ...baseConfig.output,
        filename: "main.js",
    }
};

export default [inlineSourceMapConfig, separateSourceMapConfig];
