import express from 'express';
import { initializeFirestore } from './utils/connection.js'; // Adjusted import

async function startApplication() {
  await initializeFirestore(); // Initialize Firestore
  const app = express();

  // Define routes and middleware here
  // Example route (ensure you have actual routes defined for your application)
  app.get('/', (req, res) => {
    res.send('Hello World!');
  });

  const port = process.env.PORT || 8080;
  app.listen(port, () => console.log(`Server listening on port ${port}`));
}

startApplication().catch(console.error);
