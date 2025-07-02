function runUnifiedProcessing() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const data = sheet.getDataRange().getValues();
  const headers = data[0];

  const outputHeaders = ['detected_languages', 'is_multilingual', 'content_style', 'processed_at', 'error'];

  // STEP 1: Determine column indices for all output headers (existing or new)
  const columnIndexMap = {};
  let maxColIndex = headers.length;
  outputHeaders.forEach(header => {
    const index = headers.indexOf(header);
    if (index !== -1) {
      columnIndexMap[header] = index + 1;
    } else {
      columnIndexMap[header] = ++maxColIndex;
      sheet.getRange(1, columnIndexMap[header]).setValue(header);
    }
  });

  const inputRows = [];
  const rowIndexMap = [];

  const langIndex = columnIndexMap['detected_languages'] - 1;
  const usernameIndex = headers.indexOf('username');
  const platformIndex = headers.indexOf('platform');

  // Check if required columns exist
  if (usernameIndex === -1 || platformIndex === -1) {
    SpreadsheetApp.getUi().alert("❌ Error: 'username' and 'platform' columns are required!");
    return;
  }

  // STEP 2: Build payload only for unprocessed rows
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const username = row[usernameIndex];
    const platform = row[platformIndex];
    const lang = row[langIndex];

    // Check if we have username/platform and haven't processed this row yet
    if (username && platform && username.toString().trim() !== '' && 
        platform.toString().trim() !== '' && 
        (!lang || lang.toString().trim() === '')) {
      
      const entry = {
        username: username.toString().trim(),
        platform: platform.toString().trim()
      };
      inputRows.push(entry);
      rowIndexMap.push(i + 1); // 1-based row number for writing later
    }
  }

  if (inputRows.length === 0) {
    SpreadsheetApp.getUi().alert("✅ No new rows to process. All rows with username/platform already have tags.");
    return;
  }

  // Update endpoint to your Railway URL
  //const endpoint = "https://taggeneration-production.up.railway.app/process";
  const endpoint = "https://45b2f8c7-b3c4-46d4-8d85-37aafc049891-00-1esu0oo34pre6.sisko.replit.dev/process";
  const batchSize = 2; // Smaller batch size since we're doing more work per request

  SpreadsheetApp.getUi().alert(`🚀 Starting processing for ${inputRows.length} rows...`);

  for (let start = 0; start < inputRows.length; start += batchSize) {
    const batch = inputRows.slice(start, start + batchSize);
    const batchRowIndices = rowIndexMap.slice(start, start + batchSize);

    const options = {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify({ rows: batch }),
      muteHttpExceptions: true
    };

    let results;
    try {
      const response = UrlFetchApp.fetch(endpoint, options);
      const responseCode = response.getResponseCode();
      
      if (responseCode === 200) {
        results = JSON.parse(response.getContentText());
      } else {
        throw new Error(`HTTP ${responseCode}: ${response.getContentText()}`);
      }
    } catch (e) {
      Logger.log("API call failed for batch starting at index " + start + ": " + e);
      SpreadsheetApp.getUi().alert(`❌ API call failed for batch ${start + 1}-${Math.min(start + batchSize, inputRows.length)}: ${e}`);
      return;
    }

    // Write results to sheet
    results.forEach((res, i) => {
      outputHeaders.forEach(header => {
        let val = res[header];
        if (Array.isArray(val)) val = val.join(', ');
        sheet.getRange(batchRowIndices[i], columnIndexMap[header]).setValue(val || '');
      });
    });
    
    // Progress update
    const progress = Math.min(start + batchSize, inputRows.length);
    Logger.log(`Processed ${progress}/${inputRows.length} rows`);
  }

  SpreadsheetApp.getUi().alert(`✅ Processing complete! Updated ${inputRows.length} rows with tags.`);
}

function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('Tag Extractor')
    .addItem('🚀 Run Unified Processing', 'runUnifiedProcessing')
    .addToUi();
} 