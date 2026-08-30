import fs from 'node:fs/promises';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';

const workbookPath = new URL('./defnendo_260630.xlsx', import.meta.url).pathname.replace(/^\/(?:([A-Za-z]:))/, '$1');
const input = await FileBlob.load(workbookPath);
const workbook = await SpreadsheetFile.importXlsx(input);

const sheets = await workbook.inspect({
  kind: 'sheet',
  include: 'id,name',
  maxChars: 6000,
});

const overview = await workbook.inspect({
  kind: 'workbook,sheet,table',
  maxChars: 12000,
  tableMaxRows: 12,
  tableMaxCols: 16,
  tableMaxCellChars: 100,
});

const formulas = await workbook.inspect({
  kind: 'formula',
  maxChars: 6000,
  options: { maxResults: 100 },
});

const comparison = await workbook.inspect({
  kind: 'table',
  sheetId: 'defnendo2020',
  range: 'A50:P86',
  include: 'values,formulas',
  maxChars: 16000,
  tableMaxRows: 40,
  tableMaxCols: 16,
});

const preview = await workbook.render({
  sheetName: 'defnendo2020',
  range: 'A1:P86',
  scale: 1,
  format: 'png',
});
await fs.writeFile(
  new URL('./deflator-preview.png', import.meta.url),
  new Uint8Array(await preview.arrayBuffer()),
);

await fs.writeFile(
  new URL('./deflator-inspection.txt', import.meta.url),
  `${sheets.ndjson}\n${overview.ndjson}\n${formulas.ndjson}\n${comparison.ndjson}\n`,
  'utf8',
);

console.log(sheets.ndjson);
console.log(overview.ndjson);
console.log(comparison.ndjson);
