"use client";

/** Query keys and hooks for every API resource. Screens never call fetch directly. */
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, isApiError, queryString, type Schemas, type User } from "./api";

type Params = Parameters<typeof queryString>[0];

export const keys = {
  me: ["me"] as const,
  orders: (params: Params) => ["orders", params] as const,
  order: (id: number) => ["order", id] as const,
  customers: (params: Params) => ["customers", params] as const,
  customer: (id: number) => ["customer", id] as const,
  products: (params: Params) => ["products", params] as const,
  product: (id: number) => ["product", id] as const,
  analytics: (name: string, params: Params) => ["analytics", name, params] as const,
  users: (params: Params) => ["users", params] as const,
  audit: (params: Params) => ["audit", params] as const,
};

// --- Auth ----------------------------------------------------------------------------------

export function useMe() {
  return useQuery({
    queryKey: keys.me,
    queryFn: ({ signal }) => api<User>("/auth/me", { signal }),
    staleTime: 5 * 60_000,
  });
}

export function useLogin() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: Schemas["LoginIn"]) => api<User>("/auth/login", { method: "POST", json: body }),
    onSuccess: (user) => {
      client.clear(); // never show the previous user's cached data
      client.setQueryData(keys.me, user);
    },
  });
}

export function useLogout() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api<void>("/auth/logout", { method: "POST" }),
    onSettled: () => client.clear(),
  });
}

// --- Lists and details ---------------------------------------------------------------------

function useList<T>(key: readonly unknown[], path: string, params: Params) {
  return useQuery({
    queryKey: key,
    queryFn: ({ signal }) => api<T>(`${path}${queryString(params)}`, { signal }),
    placeholderData: keepPreviousData, // keep the table on screen while the next page loads
  });
}

export const useOrders = (params: Params) =>
  useList<Schemas["Page_OrderSummary_"]>(keys.orders(params), "/orders", params);
export const useCustomers = (params: Params) =>
  useList<Schemas["Page_CustomerOut_"]>(keys.customers(params), "/customers", params);
export const useProducts = (params: Params) =>
  useList<Schemas["Page_ProductOut_"]>(keys.products(params), "/products", params);
export const useUsers = (params: Params) =>
  useList<Schemas["Page_UserOut_"]>(keys.users(params), "/users", params);
export const useAudit = (params: Params) =>
  useList<Schemas["Page_AuditEntryOut_"]>(keys.audit(params), "/audit", params);

export const useOrder = (id: number) =>
  useQuery({ queryKey: keys.order(id), queryFn: ({ signal }) => api<Schemas["OrderDetail"]>(`/orders/${id}`, { signal }) });
export const useCustomer = (id: number, enabled = true) =>
  useQuery({
    queryKey: keys.customer(id),
    queryFn: ({ signal }) => api<Schemas["CustomerDetail"]>(`/customers/${id}`, { signal }),
    enabled,
  });
export const useProduct = (id: number, enabled = true) =>
  useQuery({
    queryKey: keys.product(id),
    queryFn: ({ signal }) => api<Schemas["ProductOut"]>(`/products/${id}`, { signal }),
    enabled,
  });

// --- Analytics -----------------------------------------------------------------------------

function useAnalytics<T>(name: string, params: Params) {
  return useQuery({
    queryKey: keys.analytics(name, params),
    queryFn: ({ signal }) => api<T>(`/analytics/${name}${queryString(params)}`, { signal }),
    placeholderData: keepPreviousData,
  });
}

export const useSummary = (params: Params) => useAnalytics<Schemas["SummaryOut"]>("summary", params);
export const useTrend = (params: Params) => useAnalytics<Schemas["TrendOut"]>("revenue-trend", params);
export const useTopProducts = (params: Params) => useAnalytics<Schemas["TopProduct"][]>("top-products", params);
export const useStatusBreakdown = (params: Params) =>
  useAnalytics<Schemas["StatusCount"][]>("status-breakdown", params);

// --- Writes --------------------------------------------------------------------------------

/**
 * After an order write: refresh lists and dashboard, seed the detail cache with the result.
 * On a version conflict, reload the order so the screen shows what the other person saved.
 */
function useOrderWrite<V>(fn: (vars: V) => Promise<Schemas["OrderDetail"]>, orderId?: number) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onError: (error) => {
      if (orderId !== undefined && isApiError(error, "stale_version")) {
        void client.invalidateQueries({ queryKey: keys.order(orderId) });
      }
    },
    onSuccess: (order) => {
      client.setQueryData(keys.order(order.id), order);
      void client.invalidateQueries({ queryKey: ["orders"] });
      void client.invalidateQueries({ queryKey: ["analytics"] });
      void client.invalidateQueries({ queryKey: ["products"] }); // stock may have changed
    },
  });
}

export const useCreateOrder = () =>
  useOrderWrite((body: Schemas["OrderCreate"]) =>
    api<Schemas["OrderDetail"]>("/orders", { method: "POST", json: body }),
  );
export const useUpdateOrder = (id: number) =>
  useOrderWrite(
    (body: Schemas["OrderUpdate"]) => api<Schemas["OrderDetail"]>(`/orders/${id}`, { method: "PATCH", json: body }),
    id,
  );
export const useTransitionOrder = (id: number) =>
  useOrderWrite(
    (body: Schemas["TransitionIn"]) =>
      api<Schemas["OrderDetail"]>(`/orders/${id}/transition`, { method: "POST", json: body }),
    id,
  );

export function useSaveCustomer(id?: number) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: Schemas["CustomerIn"]) =>
      id === undefined
        ? api<Schemas["CustomerDetail"]>("/customers", { method: "POST", json: body })
        : api<Schemas["CustomerDetail"]>(`/customers/${id}`, { method: "PATCH", json: body }),
    onSuccess: (customer) => {
      client.setQueryData(keys.customer(customer.id), customer);
      void client.invalidateQueries({ queryKey: ["customers"] });
    },
  });
}

export function useSaveProduct(id?: number) {
  const client = useQueryClient();
  return useMutation({
    // Edits send only changed fields (ProductPatch), so saving a name never overwrites stock
    // that changed through order confirmations since the form was loaded.
    mutationFn: (body: Schemas["ProductIn"] | Schemas["ProductPatch"]) =>
      id === undefined
        ? api<Schemas["ProductOut"]>("/products", { method: "POST", json: body })
        : api<Schemas["ProductOut"]>(`/products/${id}`, { method: "PATCH", json: body }),
    onSuccess: (product) => {
      client.setQueryData(keys.product(product.id), product);
      void client.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

export function useUpdateUser() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: Schemas["UserUpdate"] & { id: number }) =>
      api<User>(`/users/${id}`, { method: "PATCH", json: body }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["users"] });
      void client.invalidateQueries({ queryKey: ["audit"] });
    },
  });
}
