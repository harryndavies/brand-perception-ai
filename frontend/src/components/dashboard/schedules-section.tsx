import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogClose,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { listSchedules, removeSchedule } from "@/services/schedules";
import { formatDate } from "@/lib/format";

export function SchedulesSection() {
  const queryClient = useQueryClient();
  const { data: schedules, isLoading } = useQuery({
    queryKey: ["schedules"],
    queryFn: listSchedules,
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => removeSchedule(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["schedules"] }),
  });

  if (isLoading) return <Skeleton className="h-20 w-full" />;
  if (!schedules?.length) return null;

  return (
    <div className="space-y-3">
      <h2 className="text-sm font-medium text-muted-foreground">Scheduled Analyses</h2>
      <div className="space-y-2">
        {schedules.map((s) => (
          <div key={s.id} className="flex items-center justify-between rounded-lg border px-4 py-3">
            <div>
              <p className="text-sm font-medium">{s.brand}</p>
              <p className="text-xs text-muted-foreground">
                Every {s.interval_days} days · Next run {formatDate(s.next_run)}
                {s.competitors.length > 0 && ` · vs ${s.competitors.join(", ")}`}
              </p>
            </div>
            <Dialog>
              <DialogTrigger render={
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-destructive hover:text-destructive"
                >
                  Cancel
                </Button>
              } />
              <DialogContent className="sm:max-w-sm">
                <DialogHeader>
                  <DialogTitle>Cancel schedule</DialogTitle>
                  <DialogDescription>
                    Stop the recurring analysis for {s.brand}? This can't be undone.
                  </DialogDescription>
                </DialogHeader>
                <DialogFooter>
                  <DialogClose render={<Button variant="outline" />}>
                    Keep
                  </DialogClose>
                  <DialogClose render={
                    <Button
                      variant="destructive"
                      onClick={() => removeMutation.mutate(s.id)}
                      disabled={removeMutation.isPending}
                    />
                  }>
                    Cancel schedule
                  </DialogClose>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        ))}
      </div>
    </div>
  );
}
