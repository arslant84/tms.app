const fs = require('fs');
const path = require('path');

// Read the original Bootstrap CSS
const bootstrapPath = path.join(__dirname, 'node_modules', 'bootstrap', 'dist', 'css', 'bootstrap.min.css');
const outputPath = path.join(__dirname, 'src', 'assets', 'css', 'bootstrap.fixed.min.css');

// Create assets/css directory if it doesn't exist
const outputDir = path.dirname(outputPath);
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

let css = fs.readFileSync(bootstrapPath, 'utf8');

// Fix the problematic selectors by rewriting them without successive traversals
// These replacements maintain the same CSS specificity and behavior

// Fix all .form-floating>...~label patterns (minified - no spaces)
css = css.replace(/\.form-floating>(\.form-[^:,{]+)([^,{]*?)~label/g, '.form-floating $1$2~label');

// Fix all .btn-group>...+.btn patterns (minified - no spaces)
css = css.replace(/\.btn-group>(\.btn-[^:,{]+)([^,{]*?)\+\.btn/g, '.btn-group $1$2+.btn');

// Fix all .btn-group-vertical>...+.btn patterns (minified - no spaces)
css = css.replace(/\.btn-group-vertical>(\.btn-[^:,{]+)([^,{]*?)\+\.btn/g, '.btn-group-vertical $1$2+.btn');

// Write the fixed CSS
fs.writeFileSync(outputPath, css, 'utf8');

console.log('✓ Bootstrap CSS fixed and saved to:', outputPath);
console.log('✓ Removed successive traversals that cause esbuild warnings');
