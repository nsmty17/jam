import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Radio,
  RadioGroup,
  FormLabel,
  LinearProgress,
  Typography,
  Alert,
  Box,
} from '@mui/material';
import { SelectChangeEvent } from '@mui/material/Select';
import { ICollection, IBulkAddRequest, getCollectionsMetadata } from '../utils/jam-api';
import { createBulkAddJobWithPolling } from '../utils/bulk-operations';

interface BulkAddModalProps {
  open: boolean;
  onClose: () => void;
  onComplete?: () => void;
  sourceCollectionId: string; // The collection we're copying FROM (current collection)
  selectedCompanyIds: number[]; // Companies selected via checkboxes
  totalCompaniesInCollection: number; // Total companies in the source collection
}

type SelectionMethod = 'selected' | 'all';

const BulkAddModal: React.FC<BulkAddModalProps> = ({ 
  open, 
  onClose, 
  onComplete,
  sourceCollectionId,
  selectedCompanyIds,
  totalCompaniesInCollection
}) => {
  const [collections, setCollections] = useState<ICollection[]>([]);
  const [selectedTargetCollectionId, setSelectedTargetCollectionId] = useState<string>('');
  const [selectionMethod, setSelectionMethod] = useState<SelectionMethod>('selected');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<number>(0);
  const [isProcessing, setIsProcessing] = useState(false);

  // Load collections on open
  useEffect(() => {
    if (open) {
      loadCollections();
    }
  }, [open]);

  const loadCollections = async () => {
    try {
      setIsLoading(true);
      const collectionsData = await getCollectionsMetadata();
      setCollections(collectionsData);
    } catch (err) {
      setError('Failed to load collections');
    } finally {
      setIsLoading(false);
    }
  };

  const handleTargetCollectionChange = (event: SelectChangeEvent) => {
    setSelectedTargetCollectionId(event.target.value);
  };

  const handleSelectionMethodChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSelectionMethod(event.target.value as SelectionMethod);
  };

  const handleSubmit = async () => {
    if (!selectedTargetCollectionId) {
      setError('Please select a target collection');
      return;
    }

    if (sourceCollectionId === selectedTargetCollectionId) {
      setError('Source and target collections cannot be the same');
      return;
    }

    if (selectionMethod === 'selected' && selectedCompanyIds.length === 0) {
      setError('No companies selected. Please select companies or choose "Add All"');
      return;
    }

    // Show warning for "Add All" option
    if (selectionMethod === 'all') {
      if (!confirm(`Are you sure you want to add ALL ${totalCompaniesInCollection} companies? This will ignore your current selection.`)) {
        return;
      }
    }

    setIsProcessing(true);
    setError(null);
    setProgress(0);

    const request: IBulkAddRequest = {
      source_collection_id: sourceCollectionId,
      target_collection_id: selectedTargetCollectionId,
      selection_kind: selectionMethod === 'all' ? 'all_matching' : 'explicit',
      selection_data: {
        ids: selectionMethod === 'all' ? undefined : selectedCompanyIds,
        total_at_snapshot: selectionMethod === 'all' ? totalCompaniesInCollection : undefined
      }
    };

    try {
      await createBulkAddJobWithPolling(request, (statusResponse) => {
        setProgress(statusResponse.progress_pct);
      });

      // Success!
      onComplete?.();
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Bulk add operation failed');
    } finally {
      setIsProcessing(false);
      setProgress(0);
    }
  };

  const handleClose = () => {
    if (!isProcessing) {
      setSelectedTargetCollectionId('');
      setSelectionMethod('selected');
      setError(null);
      setProgress(0);
      onClose();
    }
  };

  const sourceCollectionName = collections.find(c => c.id === sourceCollectionId)?.collection_name || '';
  const availableTargetCollections = collections.filter(c => c.id !== sourceCollectionId);

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Bulk Add Companies</DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {isProcessing && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" sx={{ mb: 1 }}>
              Processing bulk add operation... {Math.round(progress)}%
            </Typography>
            <LinearProgress variant="determinate" value={progress} />
          </Box>
        )}

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {/* Source Collection Info */}
          <Typography variant="body2" color="text.secondary">
            From: <strong>{sourceCollectionName}</strong>
          </Typography>

          {/* Target Collection Selection */}
          <FormControl fullWidth disabled={isProcessing}>
            <InputLabel>Target Collection (add to)</InputLabel>
            <Select
              value={selectedTargetCollectionId}
              label="Target Collection (add to)"
              onChange={handleTargetCollectionChange}
            >
              {availableTargetCollections.map((collection) => (
                <MenuItem key={collection.id} value={collection.id}>
                  {collection.collection_name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Selection Method */}
          <FormControl component="fieldset" disabled={isProcessing}>
            <FormLabel component="legend">What to add?</FormLabel>
            <RadioGroup
              value={selectionMethod}
              onChange={handleSelectionMethodChange}
            >
              <FormControlLabel 
                value="selected" 
                control={<Radio />} 
                label={`Add selected companies (${selectedCompanyIds.length} selected)`} 
                disabled={selectedCompanyIds.length === 0}
              />
              <FormControlLabel 
                value="all" 
                control={<Radio />} 
                label={`Add ALL companies from ${sourceCollectionName} (${totalCompaniesInCollection} total)`} 
              />
            </RadioGroup>
          </FormControl>

          {selectionMethod === 'all' && (
            <Alert severity="warning" sx={{ mt: 1 }}>
              This will add ALL {totalCompaniesInCollection} companies and ignore your current selection.
            </Alert>
          )}

          {isLoading && (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
              <Typography variant="body2">Loading collections...</Typography>
            </Box>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={isProcessing}>
          Cancel
        </Button>
        <Button 
          onClick={handleSubmit} 
          variant="contained"
          disabled={
            isProcessing || 
            !selectedTargetCollectionId ||
            (selectionMethod === 'selected' && selectedCompanyIds.length === 0)
          }
        >
          {isProcessing ? 'Processing...' : 'Add Companies'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default BulkAddModal;
