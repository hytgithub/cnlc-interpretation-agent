import { Blocks, Plug, Trash2 } from 'lucide-react';
import { useCallback, useState } from 'react';

import type { SkillView } from '@/api';
import { skillApi } from '@/api';
import { ResourceDetailDrawer } from '@/components/drawer/ResourceDetailDrawer.tsx';
import { ResourcePanel } from '@/components/hub/ResourcePanel.tsx';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar.tsx';
import { Button } from '@/components/ui/button.tsx';
import {
	Empty,
	EmptyDescription,
	EmptyHeader,
	EmptyMedia,
	EmptyTitle,
} from '@/components/ui/empty.tsx';
import {
	Item,
	ItemActions,
	ItemContent,
	ItemDescription,
	ItemGroup,
	ItemMedia,
	ItemTitle,
} from '@/components/ui/item.tsx';
import { Spinner } from '@/components/ui/spinner.tsx';
import { useResourceDrawer } from '@/hooks/useResourceDrawer.ts';
import { useTranslation } from '@/i18n/useI18n';
import { avatarTint } from '@/utils/common';

export interface MinePanelProps {
	skills: SkillView[];
	loading: boolean;
	onRemove: (skillId: string) => void;
}

export function MinePanel({ skills, loading, onRemove }: MinePanelProps) {
	const { t } = useTranslation();
	const [query, setQuery] = useState('');
	// The list view omits SKILL.md; the detail endpoint carries it.
	const drawer = useResourceDrawer(
		useCallback((skill) => skillApi.get((skill as SkillView).id), []),
	);

	// Filtered client-side: the library is the user's own and small, so a
	// round trip per keystroke would buy nothing.
	const needle = query.trim().toLowerCase();
	const shown = needle
		? skills.filter((skill) =>
				[skill.name, skill.display_name ?? '', skill.description, ...skill.tags].some((field) =>
					field.toLowerCase().includes(needle),
				),
			)
		: skills;

	return (
		<ResourcePanel
			title={t('common.my-skill')}
			description={t('skill.mineDescription')}
			icon={<Plug className="size-5 text-muted-foreground" />}
			search={
				// Hidden while there is nothing to search through.
				skills.length > 0
					? {
							value: query,
							onChange: setQuery,
							placeholder: t('skill.mineSearchPlaceholder'),
						}
					: undefined
			}
		>
			{loading ? (
				<div className="flex justify-center py-10">
					<Spinner />
				</div>
			) : skills.length === 0 ? (
				<Empty className="border-none py-10">
					<EmptyHeader>
						<EmptyMedia variant="icon">
							<Plug />
						</EmptyMedia>
						<EmptyTitle>{t('skill.mineEmptyTitle')}</EmptyTitle>
						<EmptyDescription>{t('skill.mineEmptyDescription')}</EmptyDescription>
					</EmptyHeader>
				</Empty>
			) : shown.length === 0 ? (
				<Empty className="border-none py-10">
					<EmptyHeader>
						<EmptyMedia variant="icon">
							<Blocks />
						</EmptyMedia>
						<EmptyTitle>{t('skill.noCardsTitle')}</EmptyTitle>
						<EmptyDescription>{t('skill.noCardsDescription')}</EmptyDescription>
					</EmptyHeader>
				</Empty>
			) : (
				<ItemGroup className="gap-0">
					{shown.map((skill) => (
						<Item
							key={skill.id}
							className="cursor-pointer hover:bg-accent/50"
							onClick={() => drawer.open(skill)}
						>
							<ItemMedia>
								<Avatar className="rounded-md">
									<AvatarImage
										src={skill.icon_url ?? undefined}
										alt={skill.display_name || skill.name}
										loading="lazy"
									/>
									<AvatarFallback className="rounded-md" style={avatarTint(skill.name)}>
										{(skill.display_name || skill.name).slice(0, 1).toUpperCase()}
									</AvatarFallback>
								</Avatar>
							</ItemMedia>

							<ItemContent>
								<ItemTitle>
									<span className="font-medium">{skill.display_name || skill.name}</span>
									{/* A hand-added skill has no hub to name. */}
									{skill.hub_id && (
										<span className="text-xs text-muted-foreground">@{skill.hub_id}</span>
									)}
									{skill.tags.slice(0, 4).map((tag) => (
										<span key={tag} className="text-xs text-muted-foreground/60">
											#{tag}
										</span>
									))}
								</ItemTitle>
								<ItemDescription className="line-clamp-1">{skill.description}</ItemDescription>
							</ItemContent>

							<ItemActions>
								{skill.version && (
									<span className="text-xs text-muted-foreground whitespace-nowrap">
										{skill.version}
									</span>
								)}
								<Button
									size="icon-sm"
									variant="ghost"
									// Deleting from the row must not also
									// open the drawer behind it.
									onClick={(e) => {
										e.stopPropagation();
										onRemove(skill.id);
									}}
									title={t('common.delete')}
								>
									<Trash2 />
								</Button>
							</ItemActions>
						</Item>
					))}
				</ItemGroup>
			)}

			<ResourceDetailDrawer
				skill={drawer.opened}
				loading={drawer.loading}
				onOpenChange={(open) => {
					if (!open) drawer.close();
				}}
				action={
					<Button
						variant="destructive"
						onClick={() => {
							if (drawer.opened) onRemove((drawer.opened as SkillView).id);
							drawer.close();
						}}
					>
						<Trash2 />
						{t('common.delete')}
					</Button>
				}
			/>
		</ResourcePanel>
	);
}
