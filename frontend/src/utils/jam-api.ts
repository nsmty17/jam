import axios from 'axios';

export interface ICompany {
    id: number;
    company_name: string;
    liked: boolean;
}

export interface ICollection {
    id: string;
    collection_name: string;
    companies: ICompany[];
    total: number;
}

export interface ICompanyBatchResponse {
    companies: ICompany[];
}

// Job-related interfaces
export interface IJobResponse {
    job_id: string;
    status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
    estimated_total?: number;
    created_at: string;
}

export interface IJobStatusResponse {
    job_id: string;
    status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
    total_items: number;
    processed_items: number;
    added_items: number;
    skipped_items: number;
    failed_items: number;
    progress_pct: number;
    error_message?: string;
}

export interface IBulkAddRequest {
    source_collection_id: string;
    target_collection_id: string;
    selection_kind: 'explicit' | 'all_matching';
    selection_data: {
        ids?: number[];
        total_at_snapshot?: number;
    };
    client_idempotency_key?: string;
}

const BASE_URL = 'http://localhost:8000';

export async function getCompanies(offset?: number, limit?: number): Promise<ICompanyBatchResponse> {
    try {
        const response = await axios.get(`${BASE_URL}/companies`, {
            params: {
                offset,
                limit,
            },
        });
        return response.data;
    } catch (error) {
        console.error('Error fetching companies:', error);
        throw error;
    }
}

export async function getCollectionsById(id: string, offset?: number, limit?: number): Promise<ICollection> {
    try {
        const response = await axios.get(`${BASE_URL}/collections/${id}`, {
            params: {
                offset,
                limit,
            },
        });
        return response.data;
    } catch (error) {
        console.error('Error fetching companies:', error);
        throw error;
    }
}

export async function getCollectionsMetadata(): Promise<ICollection[]> {
    try {
        const response = await axios.get(`${BASE_URL}/collections`);
        return response.data;
    } catch (error) {
        console.error('Error fetching collections:', error);
        throw error;
    }
}

// Job API functions
export async function createBulkAddJob(request: IBulkAddRequest): Promise<IJobResponse> {
    try {
        const response = await axios.post(`${BASE_URL}/jobs/bulk-add`, request);
        return response.data;
    } catch (error) {
        console.error('Error creating bulk add job:', error);
        throw error;
    }
}

export async function getJobStatus(jobId: string): Promise<IJobStatusResponse> {
    try {
        const response = await axios.get(`${BASE_URL}/jobs/${jobId}`);
        return response.data;
    } catch (error) {
        console.error('Error fetching job status:', error);
        throw error;
    }
}

export async function cancelJob(jobId: string): Promise<{ message: string; job_id: string }> {
    try {
        const response = await axios.post(`${BASE_URL}/jobs/${jobId}/cancel`);
        return response.data;
    } catch (error) {
        console.error('Error cancelling job:', error);
        throw error;
    }
}