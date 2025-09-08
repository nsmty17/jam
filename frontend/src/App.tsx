import "./App.css";

import CssBaseline from "@mui/material/CssBaseline";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { useEffect, useState } from "react";
import CompanyTable from "./components/CompanyTable";
import { getCollectionsMetadata } from "./utils/jam-api";
import useApi from "./utils/useApi";

const darkTheme = createTheme({
  palette: {
    mode: "dark",
    background: {
      default: "#ffc0cb", // Light pink background
    },
    text: {
      primary: "#000000", // Black text for better readability
      secondary: "#333333", // Dark gray for secondary text
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          color: "#000000", // Black text for buttons
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          backgroundColor: "#ffffff", // White background for modals
          color: "#000000", // Black text in modals
        },
      },
    },
    MuiModal: {
      styleOverrides: {
        root: {
          "& .MuiPaper-root": {
            backgroundColor: "#ffffff", // White background for modal content
            color: "#000000", // Black text in modals
          },
        },
      },
    },
  },
});

function App() {
  const [selectedCollectionId, setSelectedCollectionId] = useState<string>();
  const { data: collectionResponse } = useApi(() => getCollectionsMetadata());

  useEffect(() => {
    setSelectedCollectionId(collectionResponse?.[0]?.id);
  }, [collectionResponse]);

  useEffect(() => {
    if (selectedCollectionId) {
      window.history.pushState({}, "", `?collection=${selectedCollectionId}`);
    }
  }, [selectedCollectionId]);

  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
            <div className="mx-8" style={{ backgroundColor: '#ffc0cb', minHeight: '100vh' }}>
        <div className="font-bold text-xl border-b p-2 mb-4 text-left" style={{ borderColor: '#000000' }}>
          Harmonic Jam
        </div>
        <div className="flex">
          <div className="w-1/5">
            <p className=" font-bold border-b mb-2 pb-2 text-left" style={{ borderColor: '#000000' }}>
              Collections
            </p>
            <div className="flex flex-col gap-2 text-left">
              {collectionResponse?.map((collection) => {
                return (
                  <div
                    className={`py-1 pl-4 hover:cursor-pointer hover:bg-orange-300 ${
                      selectedCollectionId === collection.id &&
                      "bg-orange-500 font-bold"
                    }`}
                    onClick={() => {
                      setSelectedCollectionId(collection.id);
                    }}
                  >
                    {collection.collection_name}
                  </div>
                );
              })}
            </div>
          </div>
          <div className="w-4/5 ml-4">
            {selectedCollectionId && (
              <CompanyTable selectedCollectionId={selectedCollectionId} />
            )}
          </div>
        </div>
      </div>
    </ThemeProvider>
  );
}

export default App;
