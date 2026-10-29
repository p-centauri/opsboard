import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { KpiTile } from "./dashboard/kpi-tile";
import { BarList } from "./dashboard/bar-list";
import { Button } from "./ui/button";
import { DataTable, type Column } from "./ui/data-table";
import { ErrorState } from "./ui/feedback";
import { Field, Input } from "./ui/field";
import { Pagination } from "./ui/pagination";
import { StatusBadge } from "./ui/status-badge";
import { ApiError } from "@/lib/api";

describe("Field", () => {
  it("labels the control and announces the error", () => {
    render(<Field label="Email" error="Enter a valid email">{(a11y) => <Input {...a11y} />}</Field>);
    const input = screen.getByLabelText("Email");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("Enter a valid email");
    expect(screen.getByRole("alert")).toHaveTextContent("Enter a valid email");
  });

  it("describes the control with its hint when valid", () => {
    render(<Field label="SKU" hint="Letters and digits">{(a11y) => <Input {...a11y} />}</Field>);
    expect(screen.getByLabelText("SKU")).toHaveAccessibleDescription("Letters and digits");
    expect(screen.getByLabelText("SKU")).toHaveAttribute("aria-invalid", "false");
  });
});

describe("Button", () => {
  it("blocks repeat clicks while pending", async () => {
    const onClick = vi.fn();
    render(<Button pending onClick={onClick}>Save</Button>);
    const button = screen.getByRole("button", { name: "Save" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    await userEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });
});

describe("StatusBadge", () => {
  it("names the status in text, not only color", () => {
    render(<StatusBadge status="cancelled" />);
    expect(screen.getByText("Cancelled")).toBeInTheDocument();
  });
});

describe("KpiTile", () => {
  it("states direction with sign and arrow, colored by whether it's good", () => {
    const { container } = render(<KpiTile label="Cancellation rate" value="7%" delta={0.25} higherIsBetter={false} comparedTo="previous 30 days" />);
    expect(screen.getByText(/\+25%/)).toHaveClass("text-danger");
    expect(container).toHaveTextContent("↑ +25% vs previous 30 days");
  });

  it("says when there's no baseline instead of showing a fake change", () => {
    render(<KpiTile label="Revenue" value="$0" delta={null} />);
    expect(screen.getByText("No data for the previous period")).toBeInTheDocument();
  });
});

describe("BarList", () => {
  it("states every value in text", () => {
    render(<BarList label="Orders by status" items={[{ key: "a", label: "Draft", value: 3, display: "3" }, { key: "b", label: "Shipped", value: 0, display: "0" }]} />);
    const list = screen.getByRole("list", { name: "Orders by status" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(2);
    expect(list).toHaveTextContent("Draft3");
  });
});

describe("DataTable", () => {
  type Row = { id: number; name: string };
  const columns: Column<Row>[] = [
    { key: "name", header: "Name", sort: "name", mobile: "title", cell: (r) => r.name },
    { key: "id", header: "ID", cell: (r) => r.id },
  ];

  it("marks the sorted column and toggles direction", async () => {
    const onSort = vi.fn();
    render(<DataTable caption="People" columns={columns} rows={[{ id: 1, name: "Ann" }]} rowKey={(r) => r.id} sort="name" onSort={onSort} />);
    const table = screen.getByRole("table", { name: "People" });
    expect(within(table).getByRole("columnheader", { name: /Name/ })).toHaveAttribute("aria-sort", "ascending");
    await userEvent.click(within(table).getByRole("button", { name: /Name/ }));
    expect(onSort).toHaveBeenCalledWith("-name");
  });
});

describe("Pagination", () => {
  it("shows the range and disables moves past the ends", async () => {
    const onPage = vi.fn();
    render(<Pagination page={1} pageSize={25} total={60} onPage={onPage} />);
    expect(screen.getByText("1–25 of 60")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(onPage).toHaveBeenCalledWith(2);
  });

  it("handles an empty result", () => {
    render(<Pagination page={1} pageSize={25} total={0} onPage={() => {}} />);
    expect(screen.getByText("0–0 of 0")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
  });
});

describe("ErrorState", () => {
  it("offers retry for transient errors", async () => {
    const onRetry = vi.fn();
    render(<ErrorState error={new ApiError(0, "network_error", "Can't reach the server.")} onRetry={onRetry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Can't reach the server.");
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalled();
  });

  it("doesn't offer a pointless retry for 403", () => {
    render(<ErrorState error={new ApiError(403, "forbidden", "Requires admin")} onRetry={() => {}} />);
    expect(screen.getByText("You don't have access to this")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Try again" })).not.toBeInTheDocument();
  });
});
