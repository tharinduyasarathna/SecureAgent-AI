
import Dashboard from "@/components/dashboard";
import ProtectedRoute from "@/components/protected-route";

export default function HomePage() {
  return (
    <ProtectedRoute>
      <Dashboard />
    </ProtectedRoute>
  );
}
