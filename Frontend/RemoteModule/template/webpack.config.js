const ModuleFederationPlugin = require("webpack/lib/container/ModuleFederationPlugin");
const mf = require("@angular-architects/module-federation/webpack");
const path = require("path");
const share = mf.share;

const sharedMappings = new mf.SharedMappings();
sharedMappings.register(
  path.join(__dirname, 'tsconfig.json'),
  []);

module.exports = {
  output: {
    uniqueName: "sdk_remote_module_package",
    publicPath: "auto",
    scriptType: 'text/javascript'
  },
  optimization: {
    runtimeChunk: false
  },   
  resolve: {
    alias: {
      ...sharedMappings.getAliases(),
        lodash: 'lodash-es',
    }
  },
  plugins: [
    new ModuleFederationPlugin({
        name: "sdk_remote_module_package",
        filename: "remoteEntry.js",
        exposes: {
            './RemoteEntry': './/src/main.ts',
        },
        shared: share({
          ...sharedMappings.getDescriptors()
        })
    }),
    sharedMappings.getPlugin()
  ],
};
