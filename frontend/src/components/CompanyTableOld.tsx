import { DataGrid } from "@mui/x-data-grid";
import { useEffect, useState } from "react";
import { Button, Box, Typography } from "@mui/material";
import { getCollectionsById, ICompany } from "../utils/jam-api";
import BulkAddModal from "./BulkAddModal";

const CompanyTable = (props: { selectedCollectionId: string }) => {
  const [response, setResponse] = useState<ICompany[]>([]);
  const [total, setTotal] = useState<number>();
  const [offset, setOffset] = useState<number>(0);
  const [pageSize, setPageSize] = useState(25);
  const [bulkAddModalOpen, setBulkAddModalOpen] = useState(false);
  const [selectedCompanyIds, setSelectedCompanyIds] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getCollectionsById(props.selectedCollectionId, offset, pageSize).then(
      (newResponse) => {
        setResponse(newResponse.companies);
        setTotal(newResponse.total);
        setLoading(false);
      }
    ).catch(() => {
      setLoading(false);
    });
  }, [props.selectedCollectionId, offset, pageSize]);

  useEffect(() => {
    setOffset(0);
    setSelectedCompanyIds([]); // Clear selections when collection changes
  }, [props.selectedCollectionId]);

  useEffect(() => {
    getCollectionsById(props.selectedCollectionId, offset, pageSize).then(
      (newResponse) => {
        setResponse(newResponse.companies);
        setTotal(newResponse.total);
      }
    );
  }, [props.selectedCollectionId, offset, pageSize]);

  // Handler for individual row selection (memoized to prevent unnecessary re-renders)
  const handleRowSelection = useCallback((companyId: number, isSelected: boolean) => {
    setSelectedCompanyIds(prev => {
      if (isSelected) {
        return [...prev, companyId];
      } else {
        return prev.filter(id => id !== companyId);
      }
    });
  }, []);

  // Handler for select all on current page (memoized)
  const handleSelectAllCurrentPage = useCallback((isSelected: boolean) => {
    const currentPageIds = response.map(company => company.id);
    setSelectedCompanyIds(prev => {
      const otherPagesSelection = prev.filter(id => !currentPageIds.includes(id));
      
      if (isSelected) {
        // Add all current page IDs
        return [...otherPagesSelection, ...currentPageIds];
      } else {
        // Remove all current page IDs
        return otherPagesSelection;
      }
    });
  }, [response]);

  // Create columns with custom selection column (memoized for performance)
  const columns: GridColDef[] = useMemo(() => [
    {
      field: 'select',
      headerName: '',
      width: 50,
      sortable: false,
      filterable: false,
      disableColumnMenu: true,
      renderHeader: () => {
        const currentPageIds = response.map(company => company.id);
        const currentPageSelectedIds = selectedCompanyIds.filter(id => currentPageIds.includes(id));
        const isAllSelected = currentPageIds.length > 0 && currentPageSelectedIds.length === currentPageIds.length;
        const isIndeterminate = currentPageSelectedIds.length > 0 && currentPageSelectedIds.length < currentPageIds.length;
        
        return (
          <Checkbox
            checked={isAllSelected}
            indeterminate={isIndeterminate}
            onChange={(e) => handleSelectAllCurrentPage(e.target.checked)}
          />
        );
      },
      renderCell: (params) => {
        const isSelected = selectedCompanyIds.includes(params.row.id);
        return (
          <Checkbox
            checked={isSelected}
            onChange={(e) => {
              e.stopPropagation();
              handleRowSelection(params.row.id, e.target.checked);
            }}
          />
        );
      },
    },
    { field: "liked", headerName: "Liked", width: 90 },
    { field: "id", headerName: "ID", width: 90 },
    { field: "company_name", headerName: "Company Name", width: 200 },
  ], [response, selectedCompanyIds, handleRowSelection, handleSelectAllCurrentPage]);

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
            {selectedCompanyIds.filter(id => response.some(company => company.id === id)).length} selected on this page
          </Typography>
        )}
      </Box>
      <DataGrid
        key={`${props.selectedCollectionId}-${offset}-${pageSize}`}
        rows={response}
        rowHeight={30}
        columns={columns}
        loading={loading}
        initialState={{
          pagination: {
            paginationModel: { page: 0, pageSize: 25 },
          },
        }}
        rowCount={total}
        pagination
        paginationMode="server"
        disableRowSelectionOnClick
        onPaginationModelChange={(newMeta) => {
          setPageSize(newMeta.pageSize);
          setOffset(newMeta.page * newMeta.pageSize);
        }}
      />
      
      <BulkAddModal
        open={bulkAddModalOpen}
        onClose={() => setBulkAddModalOpen(false)}
        sourceCollectionId={props.selectedCollectionId}
        selectedCompanyIds={selectedCompanyIds}
        totalCompaniesInCollection={total || 0}
        onComplete={() => {
          // Refresh the table data
          getCollectionsById(props.selectedCollectionId, offset, pageSize).then(
            (newResponse) => {
              setResponse(newResponse.companies);
              setTotal(newResponse.total);
            }
          );
          setSelectedCompanyIds([]); // Clear selections after completion
        }}
      />
    </div>
  );
};

export default CompanyTable;
