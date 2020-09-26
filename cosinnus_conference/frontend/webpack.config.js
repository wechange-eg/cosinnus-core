const path = require('path')

module.exports = {
  /**
   * This is the main entry point for your application, it's the first file
   * that runs in the main process.
   */
  mode: 'production',
  entry: './src/index.tsx',
  output: {
    filename: '[name].js',
    path: path.resolve(__dirname, '../static/conference')
  },
  module: {
    rules: require('./webpack.rules')
  },
  resolve: {
    extensions: ['.js', '.ts', '.jsx', '.tsx', '.css', '.json']
  }
};