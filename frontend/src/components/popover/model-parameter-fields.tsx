import { ChevronDown } from 'lucide-react';

import type { ParameterProperty } from './model-parameter-schema';
import { resolveType } from './model-parameter-schema';
import { Button } from '@/components/ui/button';
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuRadioGroup,
	DropdownMenuRadioItem,
	DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu.tsx';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';

// ---------------------------------------------------------------------------
// Field components
// ---------------------------------------------------------------------------
export interface FieldProps {
	id: string;
	label: string;
	required: boolean;
	prop: ParameterProperty;
	value: unknown;
	onChange: (next: unknown) => void;
}

export function BooleanField({ id, label, prop, value, onChange }: FieldProps) {
	return (
		<>
			<Label htmlFor={id} className="whitespace-nowrap">
				{label}
			</Label>
			<Switch
				id={id}
				checked={value !== undefined ? !!value : !!prop.default}
				onCheckedChange={(checked) => onChange(!!checked)}
			/>
		</>
	);
}

export function EnumField({ id, label, required, prop, value, onChange }: FieldProps) {
	const enumValues = resolveType(prop).enumValues ?? [];
	// TODO: experiment with using prop.description as placeholder text
	const displayValue = value !== undefined && value !== null ? String(value) : '';

	return (
		<>
			<Label htmlFor={id} className="whitespace-nowrap">
				{label}
				{required && <span className="text-destructive ml-0.5">*</span>}
			</Label>
			<DropdownMenu>
				<DropdownMenuTrigger asChild>
					<Button id={id} variant="outline" className="w-full justify-between gap-1">
						<span className="truncate">{displayValue}</span>
						<ChevronDown className="size-3.5 opacity-50 shrink-0" />
					</Button>
				</DropdownMenuTrigger>
				<DropdownMenuContent
					align="start"
					className="max-h-60 overflow-y-auto"
					onPointerDown={(e) => e.stopPropagation()}
				>
					<DropdownMenuRadioGroup value={displayValue} onValueChange={(v) => onChange(v)}>
						{enumValues.map((opt) => (
							<DropdownMenuRadioItem key={String(opt)} value={String(opt)}>
								{String(opt)}
							</DropdownMenuRadioItem>
						))}
					</DropdownMenuRadioGroup>
				</DropdownMenuContent>
			</DropdownMenu>
		</>
	);
}

export function NumberField({ id, label, required, prop, value, onChange }: FieldProps) {
	const { type: effectiveType } = resolveType(prop);

	return (
		<>
			<Label htmlFor={id} className="whitespace-nowrap">
				{label}
				{required && <span className="text-destructive ml-0.5">*</span>}
			</Label>
			<Input
				id={id}
				type="number"
				value={value !== undefined ? String(value) : ''}
				placeholder={prop.default != null ? String(prop.default) : undefined}
				min={prop.minimum}
				max={prop.maximum}
				step={effectiveType === 'number' ? 'any' : undefined}
				onChange={(e) => {
					const raw = e.target.value;
					onChange(raw === '' ? undefined : Number(raw));
				}}
				onBlur={(e) => {
					if (e.target.value === '') return;
					let num = Number(e.target.value);
					if (prop.minimum !== undefined && num < prop.minimum) num = prop.minimum;
					if (prop.maximum !== undefined && num > prop.maximum) num = prop.maximum;
					if (prop.exclusiveMinimum !== undefined && num <= prop.exclusiveMinimum)
						num = prop.exclusiveMinimum + (effectiveType === 'integer' ? 1 : Number.EPSILON);
					if (prop.exclusiveMaximum !== undefined && num >= prop.exclusiveMaximum)
						num = prop.exclusiveMaximum - (effectiveType === 'integer' ? 1 : Number.EPSILON);
					if (num !== Number(e.target.value)) onChange(num);
				}}
			/>
		</>
	);
}

export function StringField({ id, label, required, prop, value, onChange }: FieldProps) {
	return (
		<>
			<Label htmlFor={id} className="whitespace-nowrap">
				{label}
				{required && <span className="text-destructive ml-0.5">*</span>}
			</Label>
			<Input
				id={id}
				type="text"
				value={value !== undefined ? String(value) : ''}
				placeholder={prop.default != null ? String(prop.default) : undefined}
				onChange={(e) => onChange(e.target.value)}
			/>
		</>
	);
}
