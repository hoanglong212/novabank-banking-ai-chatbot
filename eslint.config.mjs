export default [{
  files: ['frontend/scripts/**/*.mjs'],
  languageOptions: { ecmaVersion: 'latest', sourceType: 'module' },
  rules: {
    'constructor-super': 'error',
    'no-dupe-args': 'error',
    'no-dupe-keys': 'error',
    'no-unreachable': 'error',
    'valid-typeof': 'error',
  },
}];
