import { request } from '@/utils/request';

export interface ClientResponse {
  id: number;
  client_id: string;
  ip_address: string;
  last_heartbeat: string;
  status: 'online' | 'offline';
  created_at: string;
}

export interface RemoveOfflineResponse {
  status: string;
  deleted_count: number;
}

export const getClients = (params: { page: number; page_size: number }) => {
  return request.get<any>({
    url: '/clients',
    params,
  });
};

export const removeOfflineClients = () => {
  return request.get<RemoveOfflineResponse>({
    url: '/clients/offline',
    method: 'delete',
  });
};
