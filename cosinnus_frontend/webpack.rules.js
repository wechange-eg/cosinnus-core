module.exports = [
    // Add support for native node modules
    {
      test: /\.node$/,
      use: 'node-loader',
    },
    {
      test: /\.tsx?$/,
      exclude: /(node_modules|.webpack)/,
      loaders: [{
        loader: 'ts-loader',
        options: {
          transpileOnly: true
        }
      },{
        loader: 'react-hot-loader/webpack'
      }]
    },
    {
      test: /\.svg$/,
      use: 'svg-url-loader',
    },
    {
      test: /\.(woff(2)?|ttf|eot)(\?v=\d+\.\d+\.\d+)?$/,
      use: [
        {
          loader: 'file-loader',
          options: {
            name: '[name].[ext]',
            outputPath: 'fonts/',
            publicPath: '../fonts/'
          }
        }
      ]
    },
    {
      test: /\.scss$/i,
      use: [
          { loader: "style-loader" },
          { loader: "css-modules-typescript-loader"},
          { loader: "css-loader", options: { modules: true } },
          { loader: "sass-loader" }
      ]
    },
    {
      test: /\.css$/i,
      use: [
          { loader: "style-loader" },
          { loader: "css-modules-typescript-loader"},
          { loader: "css-loader", options: { modules: true } }
      ]
    },
  ];
  