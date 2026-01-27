import typescript from '@rollup/plugin-typescript';
import resolve from '@rollup/plugin-node-resolve';

export default [
  {
    input: 'src/background/background.ts',
    output: {
      file: 'dist/background/background.js',
      format: 'iife',
      name: 'MaestraBackground'
    },
    plugins: [resolve(), typescript({ tsconfig: './tsconfig.json' })]
  },
  {
    input: 'src/content/content.ts',
    output: {
      file: 'dist/content/content.js',
      format: 'iife',
      name: 'MaestraContent'
    },
    plugins: [resolve(), typescript({ tsconfig: './tsconfig.json' })]
  }
];
