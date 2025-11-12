// Constants for Secret Manager paths
const SERVICE_URL_SECRET_PATH = 'projects/galactic-data/secrets/CLOUD_RUN_SERVICE_URL/versions/latest';

function getSecretFromPath(secretPath) {
  // Validate secretPath format
  const secretPathPattern = /^projects\/[^\/]+\/secrets\/[^\/]+\/versions\/(latest|\d+)$/;
  if (typeof secretPath === 'undefined' || !secretPathPattern.test(secretPath)) {
      Logger.log('Error: Invalid or undefined secretPath');
      return; // Or throw an error for invalid path
  }

  // Append ':access' to the secretPath to specifically request the secret's value
  const url = `https://secretmanager.googleapis.com/v1/${secretPath}:access`;
  const options = {
      'method': 'get',
      'headers': {
          'Authorization': 'Bearer ' + ScriptApp.getOAuthToken(),
      },
      'muteHttpExceptions': true
  };

  const response = UrlFetchApp.fetch(url, options);
  const responseCode = response.getResponseCode();
  const responseText = response.getContentText();

  if (responseCode === 200) {
      const secretResponse = JSON.parse(responseText);

      if (secretResponse.payload && secretResponse.payload.data) {
          const decodedSecret = Utilities.newBlob(Utilities.base64Decode(secretResponse.payload.data)).getDataAsString();
          return decodedSecret;
      } else {
          Logger.log('Secret payload or data not found in the response.');
          throw new Error('Secret payload or data not found in response for the provided path.');
      }
  } else {
      Logger.log('Failed to retrieve secret due to an error.');
      throw new Error('Failed to retrieve secret for the provided path with response code: ' + responseCode);
  }
}

function getGalacticData() {
  Logger.log("Attempting to fetch service URL.");
  var serviceUrl = getSecretFromPath(SERVICE_URL_SECRET_PATH);
  if (!serviceUrl) {
    Logger.log("Failed to fetch service URL.");
    return [];
  }
  Logger.log("Service URL fetched successfully.");

  try {
    var options = {
      'method': 'get',
      'muteHttpExceptions': true
    };

    var response = UrlFetchApp.fetch(serviceUrl, options);
    var responseCode = response.getResponseCode();
    var responseData = response.getContentText();
    
    Logger.log('Response Code: ' + responseCode);
    Logger.log('Response Data: ' + responseData);

    if (responseCode === 200) {
      var contentType = response.getHeaders()['Content-Type'] || '';
      if (contentType.includes('application/json')) {
        var jsonData = JSON.parse(responseData);
        var pricesArray = [];
        for (var token in jsonData) {
          var tokenData = jsonData[token];
          // Create a sub-array for each token, matching the order of your sheet's columns
          pricesArray.push([tokenData.name, tokenData.symbol, tokenData.price, tokenData.lastUpdated]);
        }
        Logger.log('Prices Array: ' + JSON.stringify(pricesArray));
        return pricesArray; // This now returns an array of rows, suitable for setValues
      } else {
        throw new Error('Invalid content type: expected application/json but received ' + contentType);
      }
    } else {
      throw new Error('Request failed with response code ' + responseCode + ' and body ' + responseData);
    }
  } catch (e) {
    Logger.log('Error: ' + e.toString());
    SpreadsheetApp.getUi().alert('Error: ' + e.toString());
  }
}
