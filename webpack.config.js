const path = require('path');
const TerserPlugin = require('terser-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const CssMinimizerPlugin = require('css-minimizer-webpack-plugin');

module.exports = {
  mode: 'production',
  entry: {
    'framer-motion-modals': './static/js/framer-motion-modals.js',
    'operator-details': './static/js/operator-details.js',
    'lazy-loading': './static/js/lazy-loading.js',
    'styles': [
      './static/css/framer-motion-animations.css',
      './static/css/style.css',
      './static/css/variables.css',
      './static/css/components.css',
      './static/css/lazy-loading.css'
    ]
  },
  output: {
    path: path.resolve(__dirname, 'static/dist'),
    filename: '[name].min.js',
    publicPath: '/static/dist/'
  },
  module: {
    rules: [
      {
        test: /\.css$/,
        use: [MiniCssExtractPlugin.loader, 'css-loader']
      }
    ]
  },
  optimization: {
    minimize: true,
    minimizer: [
      new TerserPlugin({
        terserOptions: {
          compress: {
            drop_console: true,
          },
          output: {
            comments: false,
          },
        },
        extractComments: false,
      }),
      new CssMinimizerPlugin({
        minimizerOptions: {
          preset: [
            'default',
            {
              discardComments: { removeAll: true },
            },
          ],
        },
      }),
    ],
  },
  plugins: [
    new MiniCssExtractPlugin({
      filename: '[name].min.css',
    })
  ]
}; 