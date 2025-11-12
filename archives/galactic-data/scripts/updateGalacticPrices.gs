function updateGalacticDataSheet() {
  var pricesData = getGalacticData();

  if (!pricesData || pricesData.length === 0) {
    Logger.log('No prices data available to update the sheet.');
    return; // Exit the function if there is no data
  }

  var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = spreadsheet.getSheetByName('galactic-data');

  // If the 'galactic-data' sheet does not exist, create it
  if (!sheet) {
    sheet = spreadsheet.insertSheet('galactic-data');
  }

  // Set headers
  var headers = ["NAME", "SYMBOL", "PRICE in USD", "LAST UPDATED"];
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);

  // Clear any existing content below the headers
  sheet.getRange('A2:Z' + sheet.getLastRow()).clearContent();

  // Apply changes to the spreadsheet
  SpreadsheetApp.flush();

  // Write the new data to the sheet starting at row 2 to preserve headers
  try {
    var startRow = 2; // Start at row 2 to avoid headers
    var range = sheet.getRange(startRow, 1, pricesData.length, headers.length);
    range.setValues(pricesData);
    Logger.log('Data written to sheet');
  } catch (e) {
    Logger.log('Failed to write data to the sheet: ' + e.toString());
  }

  // Apply changes to the spreadsheet after writing the data
  SpreadsheetApp.flush();
  Logger.log('SpreadsheetApp.flush() called after writing data');
}
