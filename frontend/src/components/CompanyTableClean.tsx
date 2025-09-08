import { DataGrid, GridPaginationModel } from "@mui/x-data-grid";
import { useEffect, useState } from "react";
import { Button, Box, Typography } from "@mui/material";
import { getCollectionsById, ICompany } from "../utils/jam-api";
import BulkAddModal from "./BulkAddModal";

const CompanyTable = (props: { selectedCollectionId: string }) => {
  const [response, setResponse] = useState<ICompany[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({
    page: 0,
    pageSize: 25,
  });
  const [bulkAddModalOpen, setBulkAddModalOpen] = useState(false);
  const [selectedCompanyIds, setSelectedCompanyIds] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);

  // Calculate offset from pagination model
  const offset = paginationModel.page * paginationModel.pageSize;

  useEffect(() => {
    setLoading(true);
    getCollectionsById(props.selectedCollectionId, offset, paginationModel.pageSize).then(
      (newResponse) => {
        setResponse(newResponse.companies);
        setTotal(newResponse.total);
        setLoading(false);
      }
    ).catch(() => {
      setLoading(false);
    });
  }, [props.selectedCollectionId, offset, paginationModel.pageSize]);

  useEffect(() => {
    // Reset pagination and selections when collection changes
    setPaginationModel({ page: 0, pageSize: 25 });
    setSelectedCompanyIds([]);
  }, [props.selectedCollectionId]);

  // Handle selection changes with proper cross-page persistence
  const handleSelectionChange = (newSelection: readonly (string | number)[]) => {
    const currentPageIds = response.map(company => company.id);
    const otherPagesSelection = selectedCompanyIds.filter(id => !currentPageIds.includes(id));
    const newSelectionNumbers = newSelection.map(id => Number(id)).filter(id => currentPageIds.includes(id));
    const updatedSelection = [...otherPagesSelection, ...newSelectionNumbers];
    setSelectedCompanyIds(updatedSelection);
  };

  // Get current page selections for DataGrid
  const currentPageSelections = selectedCompanyIds
    .filter(id => response.some(company => company.id === id))
    .map(id => String(id));

  const handlePaginationChange = (newPaginationModel: GridPaginationModel) => {
    setPaginationModel(newPaginationModel);
  };

  return (
    <div style={{ height: 600, width: "100%" }}>
      <Box sx={{ mb: 2 }}>
        <Button 
          variant="contained" 
          onClick={() => setBulkAddModalOpen(true)}
          disabled={selectedCompanyIds.length === 0}
        >
          Bulk Add Companies ({selectedCompanyIds.length} selected across all pages)
        </Button>
        {selectedCompanyIds.length > 0 && (
          <Typography variant="caption" sx={{ ml: 2, color: 'text.secondary' }}>
            {currentPageSelections.length} selected on this page
          </Typography>
        )}
      </Box>
      
      <DataGrid
        rows={response}
        rowHeight={30}
        loading={loading}
        columns={[
          { field: "liked", headerName: "Liked", width: 90 },
          { field: "id", headerName: "ID", width: 90 },
          { field: "company_name", headerName: "Company Name", width: 200 },
        ]}
        rowCount={total}
        pagination
        paginationMode="server"
        paginationModel={paginationModel}
        onPaginationModelChange={handlePaginationChange}
        checkboxSelection
        disableRowSelectionOnClick
        onRowSelectionModelChange={handleSelectionChange}
        rowSelectionModel={currentPageSelections}
        pageSizeOptions={[25, 50, 100]}
      />
      
      <BulkAddModal
        open={bulkAddModalOpen}
        onClose={() => setBulkAddModalOpen(false)}
        sourceCollectionId={props.selectedCollectionId}
        selectedCompanyIds={selectedCompanyIds}
        totalCompaniesInCollection={total}
        onComplete={() => {
          // Refresh the table data
          setLoading(true);
          getCollectionsById(props.selectedCollectionId, offset, paginationModel.pageSize).then(
            (newResponse) => {
              setResponse(newResponse.companies);
              setTotal(newResponse.total);
              setLoading(false);
            }
          );
          setSelectedCompanyIds([]); // Clear selections after completion
        }}
      />
    </div>
  );
};

export default CompanyTable;
