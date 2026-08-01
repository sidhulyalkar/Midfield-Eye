import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  createContext,
  useContext,
  useMemo,
  type PropsWithChildren,
} from "react";
import { createDataSource } from "../data/dataSources";
import type { ShowcaseDataSource } from "../data/ShowcaseDataSource";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const DataSourceContext = createContext<ShowcaseDataSource | null>(null);

export function AppProviders({ children }: PropsWithChildren) {
  const source = useMemo(() => createDataSource(), []);
  return (
    <QueryClientProvider client={queryClient}>
      <DataSourceContext.Provider value={source}>
        {children}
      </DataSourceContext.Provider>
    </QueryClientProvider>
  );
}

export function useDataSource(): ShowcaseDataSource {
  const value = useContext(DataSourceContext);
  if (!value) throw new Error("ShowcaseDataSource is unavailable.");
  return value;
}
