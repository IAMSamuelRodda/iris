// Add a custom menu to the Google Sheet on open
function onOpen() {
  var ui = SpreadsheetApp.getUi();
  // Create a new menu
  ui.createMenu('Galactic Data')
    .addItem('Update Data', 'updateGalacticDataSheet') // Assuming this is the main function you've provided
    .addToUi();
}

