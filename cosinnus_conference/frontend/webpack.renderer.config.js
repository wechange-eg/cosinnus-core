/* eslint-disable @typescript-eslint/no-var-requires, import/no-commonjs */
const Dotenv = require('dotenv-webpack');
const ForkTsCheckerWebpackPlugin = require('fork-ts-checker-webpack-plugin');

const rules = require('./webpack.rules');

module.exports = {
  module: {
    rules,
  },
  plugins: [
    new Dotenv(),
    new ForkTsCheckerWebpackPlugin({
      async: false
    })
  ],
  resolve: {
    extensions: ['.js', '.ts', '.jsx', '.tsx', '.css']
  }
};
