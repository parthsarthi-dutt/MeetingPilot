import { useEffect } from "react";
import { wsClient } from "@/lib/api/ws";
import { useQueryClient } from "@tanstack/react-query";
import type { MeetingDetail, WorkflowLogEntry, Checklist } from "@/lib/api/types";

export function useMeetingWebSocket(meetingId: string | undefined) {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!meetingId) return;

    wsClient.joinMeeting(meetingId);

    const onStatusChanged = (data: any) => {
      if (data.meeting_id === meetingId) {
        queryClient.setQueryData(["meeting", meetingId], (old: MeetingDetail | undefined) => {
          if (!old) return old;
          return { ...old, status: data.status };
        });
        queryClient.invalidateQueries({ queryKey: ["meetings"] });
        queryClient.invalidateQueries({ queryKey: ["credits"] });
      }
    };

    const onLogAppended = (data: any) => {
      if (data.meeting_id === meetingId) {
        queryClient.setQueryData(["meeting-workflow-logs", meetingId], (old: WorkflowLogEntry[] | undefined) => {
          const logs = old || [];
          return [...logs, data.log_entry];
        });
      }
    };

    const onChecklistUpdated = (data: any) => {
      if (data.meeting_id === meetingId || !data.meeting_id) { 
        queryClient.setQueryData(["meeting", meetingId], (old: MeetingDetail | undefined) => {
          if (!old) return old;
          return {
            ...old,
            checklist: {
              items: data.items ?? old.checklist?.items ?? [],
              status: data.status ?? old.checklist?.status ?? "not_started"
            }
          };
        });
      }
    };

    wsClient.on("meeting_status_changed", onStatusChanged);
    wsClient.on("workflow_log_appended", onLogAppended);
    wsClient.on("checklist_updated", onChecklistUpdated);

    return () => {
      wsClient.off("meeting_status_changed", onStatusChanged);
      wsClient.off("workflow_log_appended", onLogAppended);
      wsClient.off("checklist_updated", onChecklistUpdated);
      wsClient.leaveMeeting(meetingId);
    };
  }, [meetingId, queryClient]);

  const tickChecklist = (agendaItemId: string, ticked: boolean) => {
    wsClient.send({
      event: "checklist_tick",
      meeting_id: meetingId,
      agenda_item_id: agendaItemId,
      ticked,
    });
  };

  const commentChecklist = (agendaItemId: string, text: string) => {
    wsClient.send({
      event: "checklist_comment",
      meeting_id: meetingId,
      agenda_item_id: agendaItemId,
      text,
    });
  };

  return { tickChecklist, commentChecklist };
}
