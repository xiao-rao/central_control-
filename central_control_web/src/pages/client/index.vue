<template>
  <div class="client-list">
    <t-card>
      <t-space direction="vertical" size="large" style="width: 100%">
        <t-space align="center" justify="end">
          <t-button theme="danger" @click="handleRemoveOffline">
            <template #icon>
              <delete-icon />
            </template>
            清理离线客户端
          </t-button>
          <t-button theme="primary" @click="refreshData">
            <template #icon>
              <refresh-icon />
            </template>
            刷新
          </t-button>
        </t-space>

        <t-table
          :data="clientList"
          :columns="columns"
          row-key="id"
          :loading="loading"
          :pagination="pagination"
          @page-change="handlePageChange"
        >
          <template #last_heartbeat="{ row }">
            {{ formatTime(row.last_heartbeat) }}
          </template>
          <template #status="{ row }">
            <t-tag :theme="row.status === 'online' ? 'success' : 'danger'">
              {{ row.status }}
            </t-tag>
          </template>
        </t-table>
      </t-space>
    </t-card>
  </div>
</template>

<script lang="ts" setup>
import { DeleteIcon, RefreshIcon } from 'tdesign-icons-vue-next';
import { MessagePlugin } from 'tdesign-vue-next';
import { onMounted, ref } from 'vue';

import { type ClientResponse, getClients, removeOfflineClients } from '@/api/client';

const loading = ref<boolean>(false);
const clientList = ref<ClientResponse[]>([]);
const pagination = ref({
  total: 0,
  pageSize: 10,
  current: 1,
});

const columns = [
  { colKey: 'client_id', title: '客户名称' },
  { colKey: 'ip_address', title: 'ip' },
  { colKey: 'last_heartbeat', title: '最后一次上报心跳' },
  {
    colKey: 'status',
    title: '状态',
    width: 100,
  },
  { colKey: 'created_at', title: '加入时间' },
];

const fetchData = async () => {
  loading.value = true;
  try {
    // 这里替换为实际的获取客户列表接口
    const data = await getClients({
      page: pagination.value.current,
      page_size: pagination.value.pageSize,
    });
    clientList.value = data.items;
    pagination.value.total = data.total;
    pagination.value.current = data.page; // 确保更新当前页码
    pagination.value.pageSize = data.page_size; // 确保更新每页大小
  } catch (error) {
    MessagePlugin.error('获取数据失败');
  } finally {
    loading.value = false;
  }
};

const handlePageChange = (pageInfo) => {
  pagination.value.current = pageInfo.current;
  pagination.value.pageSize = pageInfo.pageSize;
  fetchData();
};

const refreshData = async (): Promise<void> => {
  loading.value = true;
  try {
    const data = await getClients({
      page: pagination.value.current,
      page_size: pagination.value.pageSize,
    });
    clientList.value = data.items;
    pagination.value.total = data.total;
    pagination.value.current = data.page; // 确保更新当前页码
    pagination.value.pageSize = data.page_size; // 确保更新每页大小
  } catch (error) {
    MessagePlugin.error('获取客户端列表失败');
  } finally {
    loading.value = false;
  }
};

const handleRemoveOffline = async (): Promise<void> => {
  try {
    const { data } = await removeOfflineClients();
    MessagePlugin.success(`成功清理 ${data.deleted_count} 个离线客户端`);
    refreshData();
  } catch (error) {
    MessagePlugin.error('清理离线客户端失败');
  }
};

const formatTime = (time: string) => {
  return new Date(time).toLocaleString();
};

onMounted(() => {
  refreshData();
});
</script>

<style lang="less" scoped>
.client-list {
  padding: 16px;

  :deep(.t-card) {
    .t-card__body {
      padding: 20px;
    }
  }
}
</style>
