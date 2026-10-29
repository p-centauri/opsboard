import type { Metadata } from "next";

import { EditOrder } from "./edit-order";

export const metadata: Metadata = { title: "Edit order" };

export default function EditOrderPage() {
  return <EditOrder />;
}
