import { useSearchParams } from "react-router";
import DifferencePublicationPage from "./DifferencePublicationPage";
import DifferenceVolumePage from "./DifferenceVolumePage";

export default function DifferenceVolumeRoute() {
  const [searchParams] = useSearchParams();
  return searchParams.get("pub") === "figure" ? (
    <DifferencePublicationPage />
  ) : (
    <DifferenceVolumePage />
  );
}
