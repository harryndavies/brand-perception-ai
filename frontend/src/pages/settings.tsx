import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";

function ApiKeysSection() {
  const { data: keys, isLoading } = useQuery({
    queryKey: ["keys"],
    queryFn: api.keys.list,
  });
  const [keyName, setKeyName] = useState("");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">API Keys</CardTitle>
        <CardDescription>
          Manage keys for programmatic access to the Brand Intelligence API.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Input
            placeholder="Key name (e.g. Production)"
            value={keyName}
            onChange={(e) => setKeyName(e.target.value)}
            className="max-w-xs"
          />
          <Button disabled={!keyName.trim()}>Create Key</Button>
        </div>

        {isLoading ? (
          <div className="space-y-2">
            {[0, 1].map((i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : !keys?.length ? (
          <p className="text-sm text-muted-foreground">No API keys created yet.</p>
        ) : (
          <div className="rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Key</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Last Used</TableHead>
                  <TableHead className="w-10" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {keys.map((key) => (
                  <TableRow key={key.id}>
                    <TableCell className="font-medium">{key.name}</TableCell>
                    <TableCell>
                      <code className="text-xs text-muted-foreground">
                        {key.prefix}...
                      </code>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(key.created_at).toLocaleDateString("en-GB")}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {key.last_used_at
                        ? new Date(key.last_used_at).toLocaleDateString("en-GB")
                        : "Never"}
                    </TableCell>
                    <TableCell>
                      <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive">
                        Revoke
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function TeamSection() {
  const { data: members, isLoading } = useQuery({
    queryKey: ["team"],
    queryFn: api.team.list,
  });
  const [email, setEmail] = useState("");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Team Members</CardTitle>
        <CardDescription>
          Invite team members to collaborate on brand analysis.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Input
            type="email"
            placeholder="colleague@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="max-w-xs"
          />
          <Button disabled={!email.trim()}>Send Invite</Button>
        </div>

        {isLoading ? (
          <div className="space-y-2">
            {[0, 1].map((i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : !members?.length ? (
          <p className="text-sm text-muted-foreground">No team members yet.</p>
        ) : (
          <div className="rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Joined</TableHead>
                  <TableHead className="w-10" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {members.map((member) => (
                  <TableRow key={member.id}>
                    <TableCell className="font-medium">{member.name}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {member.email}
                    </TableCell>
                    <TableCell>
                      <Badge variant={member.role === "admin" ? "default" : "secondary"}>
                        {member.role}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(member.joined_at).toLocaleDateString("en-GB")}
                    </TableCell>
                    <TableCell>
                      {member.role !== "admin" && (
                        <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive">
                          Remove
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function BillingSection() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Billing</CardTitle>
        <CardDescription>
          Manage your subscription and payment details.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between rounded-lg border p-4">
          <div>
            <p className="font-medium">Pro Plan</p>
            <p className="text-sm text-muted-foreground">
              100 analyses per month · 5 team members
            </p>
          </div>
          <Button variant="outline">Manage Subscription</Button>
        </div>
      </CardContent>
    </Card>
  );
}

export function SettingsPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Manage your account, team, and API access.
        </p>
      </div>

      <ApiKeysSection />
      <Separator />
      <TeamSection />
      <Separator />
      <BillingSection />
    </div>
  );
}
