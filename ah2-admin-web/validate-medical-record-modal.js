import fs from 'fs';
import path from 'path';
import { parse } from '@vue/compiler-sfc';

const filePath = 'src/components/medical-records/MedicalRecordModal.vue';

try {
  const content = fs.readFileSync(filePath, 'utf-8');
  const result = parse(content, { filename: path.basename(filePath) });

  if (result.errors && result.errors.length > 0) {
    console.error('Vue Compilation Errors:');
    result.errors.forEach((error, index) => {
      console.error(`Error ${index + 1}:`, error.message);
    });
    process.exit(1);
  }

  console.log('Vue file syntax validation: SUCCESS');
  console.log('File parsed successfully with no errors.');
  process.exit(0);
} catch (error) {
  console.error('Error parsing Vue file:', error.message);
  console.error(error);
  process.exit(1);
}
