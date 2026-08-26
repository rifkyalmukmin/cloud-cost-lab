import { ResourceDetailContent } from "@/components/resources/resource-detail-content";

export default async function ResourceDetailPage(props: PageProps<"/resources/[id]">) {
  const { id } = await props.params;
  return (
    <main className="flex-1 p-6 max-w-7xl mx-auto w-full">
      <ResourceDetailContent resourceId={id} />
    </main>
  );
}
